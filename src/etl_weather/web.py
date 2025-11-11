from __future__ import annotations

import os
from pathlib import Path
from typing import List

import pandas as pd
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from . import fetch as fetch_mod
from . import transform as transform_mod
from .utils import slugify

# Load environment variables from .env file (keep imports at top for linting)
load_dotenv()


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(str(path))
    # parse dates where possible
    parse_dates = ["date"] if path.name.endswith("_daily.csv") else ["time", "date"]
    try:
        return pd.read_csv(path, parse_dates=parse_dates)
    except Exception:
        # fallback without parse dates
        return pd.read_csv(path)


async def _fetch_provinces() -> list[dict]:
    url = "https://wilayah.id/api/provinces.json"
    headers = {"Cache-Control": "no-cache", "Pragma": "no-cache"}
    try:
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            import logging

            logging.info(f"Provinces raw response: {r.text[:200]}...")
            data = r.json()
            # Transform the data to ensure it has the correct structure
            provinces = []
            if isinstance(data, dict):
                if "provinces" in data:
                    provinces = data["provinces"]
                elif "data" in data:
                    provinces = data["data"]
                else:
                    provinces = [{"id": k, "name": v} for k, v in data.items()]
            elif isinstance(data, list):
                provinces = data

            # Ensure each province has the required fields
            formatted_provinces = []
            for prov in provinces:
                if isinstance(prov, dict):
                    prov_id = (
                        prov.get("id") or prov.get("province_id") or prov.get("code")
                    )
                    prov_name = (
                        prov.get("name")
                        or prov.get("province_name")
                        or prov.get("nama")
                    )
                    if prov_id and prov_name:
                        formatted_provinces.append(
                            {"id": str(prov_id), "name": prov_name}
                        )

            logging.info(f"Formatted provinces: {formatted_provinces}")
            return formatted_provinces
    except httpx.HTTPError as e:
        import logging

        logging.error(f"Error fetching provinces: {str(e)}")
        return []


async def _fetch_regencies(province_code: str) -> list[dict]:
    # The API expects just the number, remove any prefix if present
    if "-" in province_code:
        province_code = province_code.split("-")[0]

    url = f"https://wilayah.id/api/regencies/{province_code}.json"
    headers = {"Cache-Control": "no-cache", "Pragma": "no-cache"}
    try:
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            import logging

            logging.info(
                f"Regencies response for {province_code}: {r.text[:200]}..."
            )  # Log first 200 chars
            data = r.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                if "data" in data:
                    return data["data"]
                if "regencies" in data:
                    return data["regencies"]
                # Handle case where the response might be directly keyed by province code
                if province_code in data:
                    return data[province_code]
            return data
    except httpx.HTTPError as e:
        import logging

        logging.error(f"Error fetching regencies: {str(e)}")
        return []


async def _geocode_search(
    query: str, count: int = 5, language: str = "id"
) -> list[dict]:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": query, "count": count, "language": language, "format": "json"}
    # Be resilient to occasional network hiccups/timeouts; keep UI responsive by returning [] on failure
    try:
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            j = r.json()
    except httpx.HTTPError:
        # On network errors or non-2xx, fail soft with empty results so the endpoint stays 200
        j = {"results": []}
    results = j.get("results") or []
    out = []
    for res in results:
        out.append(
            {
                "name": res.get("name"),
                "country": res.get("country"),
                "admin1": res.get("admin1"),
                "lat": res.get("latitude"),
                "lon": res.get("longitude"),
                "timezone": res.get("timezone"),
            }
        )
    return out


app = FastAPI(title="ETL Weather API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # relax for dev; tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add headers middleware to prevent caching
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# API Routes
@app.get("/api/provinces")
async def get_provinces() -> dict:
    provinces = await _fetch_provinces()
    return {"results": provinces}


@app.get("/api/regencies/{province_code}")
async def get_regencies(province_code: str) -> dict:
    regencies = await _fetch_regencies(province_code)
    return {"results": regencies}


# Prefer the source tree during development; fall back to package path when installed.
def _resolve_webui_dir() -> Path:
    # 1) Explicit override via env var
    env_dir = os.getenv("ETL_WEATHER_WEBUI_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.exists():
            return p
    # 2) Source tree: <repo>/src/etl_weather/webui
    here = Path(__file__).resolve()
    src_candidate = here.parents[2] / "src" / "etl_weather" / "webui"
    if src_candidate.exists():
        return src_candidate
    # 3) Package-installed path: <site-packages>/etl_weather/webui
    pkg_candidate = here.parent / "webui"
    return pkg_candidate


WEB_DIR = _resolve_webui_dir()
if not WEB_DIR.exists():
    raise RuntimeError(
        f"Web UI directory not found: {WEB_DIR}. Set ETL_WEATHER_WEBUI_DIR to the 'webui' folder "
        "or install in editable mode (pip install -e .) so static files are available."
    )
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/city/funfact/{city}")
async def get_city_funfact(
    city: str,
    background_tasks: BackgroundTasks,
    fresh: bool = Query(
        False, description="Paksa minta varian baru (bisa lebih lambat)"
    ),
    fast: bool = Query(
        False,
        description="Cepat: jika ada cache, balas segera dan refresh di background",
    ),
) -> dict:
    from .utils import get_city_fun_fact, get_cached_city_fun_fact

    try:
        # Fast mode: return cached instantly if available, and refresh in background
        if fast:
            cached = get_cached_city_fun_fact(city)
            if cached:
                background_tasks.add_task(get_city_fun_fact, city, True)
                return {"city": city, "fun_fact": cached, "source": "cache-fast"}
        # Normal path: generate (may be slower), respecting 'fresh'
        fun_fact = get_city_fun_fact(city, fresh=fresh)
        return {"city": city, "fun_fact": fun_fact, "source": "gemini"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/ai/status")
async def ai_status() -> dict:
    """Diagnostic endpoint: checks Gemini env/model availability without exposing secrets."""
    import os

    try:
        import google.generativeai as genai  # type: ignore

        sdk_ok = True
    except Exception:
        genai = None
        sdk_ok = False

    api_key_present = bool(os.getenv("GEMINI_API_KEY"))
    model_env = os.getenv("GEMINI_MODEL") or "(unset)"

    gen_ok = False
    err = None
    if api_key_present and sdk_ok and genai is not None and model_env != "(unset)":
        try:
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            # Try candidates from env (comma-separated allowed) and add 'models/' variants
            env_list = [s.strip() for s in model_env.split(",") if s.strip()]
            priority = ["gemini-2.5-flash", "gemini-2.5-pro"]
            base = env_list + priority
            expanded = []
            for name in base:
                if name.startswith("models/"):
                    expanded.append(name)
                    expanded.append(name.replace("models/", "", 1))
                else:
                    expanded.append(name)
                    expanded.append("models/" + name)
            # dedupe
            seen = set()
            candidates = [x for x in expanded if not (x in seen or seen.add(x))]
            r = None
            last_err = None
            if hasattr(genai, "GenerativeModel"):
                for cand in candidates:
                    try:
                        m = genai.GenerativeModel(model_name=cand)
                        r = m.generate_content(
                            "Tes status AI singkat.",
                            generation_config={
                                "temperature": 0.2,
                                "max_output_tokens": 8,
                            },
                        )
                        gen_ok = True if r else False
                        model_env = cand
                        break
                    except Exception as e:
                        last_err = f"{e.__class__.__name__}: {str(e)[:180]}"
            if not gen_ok and hasattr(genai, "generate_text"):
                for cand in candidates:
                    try:
                        r = genai.generate_text(model=cand, prompt="Tes.")
                        gen_ok = True if r else False
                        model_env = cand
                        break
                    except Exception as e:
                        last_err = f"{e.__class__.__name__}: {str(e)[:180]}"
            if not gen_ok:
                err = last_err
        except Exception as e:
            err = f"{e.__class__.__name__}: {str(e)[:180]}"

    return {
        "sdk": sdk_ok,
        "api_key": api_key_present,
        "model": model_env,
        "generate_ok": gen_ok,
        "error": err,
    }


@app.get("/search")
async def search(
    q: str = Query(..., description="Nama kota untuk dicari"), count: int = 5
) -> dict:
    if not q.strip():
        raise HTTPException(status_code=400, detail="Parameter q kosong")
    results = await _geocode_search(q.strip(), count=count)
    return {"query": q, "count": len(results), "results": results}


def _ensure_daily(city: str, refresh: bool) -> Path:
    slug = slugify(city)
    daily_path = Path("data/processed") / f"{slug}_daily.csv"
    if refresh or not daily_path.exists():
        # Always try to fetch first if refresh is requested
        if refresh:
            fetch_mod.run(city, days=settings.days, timezone=settings.timezone)
        # Transform (will raise if raw not present and refresh was false)
        transform_mod.run(city)
    return daily_path


def _ensure_hourly(city: str, refresh: bool) -> Path:
    slug = slugify(city)
    hourly_path = Path("data/processed") / f"{slug}_hourly.csv"
    if refresh or not hourly_path.exists():
        if refresh:
            fetch_mod.run(city, days=settings.days, timezone=settings.timezone)
        transform_mod.run_hourly(city)
    return hourly_path


@app.get("/data/daily")
async def data_daily(city: str, refresh: bool = False) -> dict:
    try:
        p = _ensure_daily(city, refresh)
        df = _load_csv(p)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Data daily tidak tersedia; set refresh=true untuk mengambil.",
        )
    records = df.to_dict(orient="records")
    return {"city": city, "count": len(records), "data": records}


@app.get("/data/hourly")
async def data_hourly(city: str, refresh: bool = False) -> dict:
    try:
        p = _ensure_hourly(city, refresh)
        df = _load_csv(p)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Data hourly tidak tersedia; set refresh=true untuk mengambil.",
        )
    records = df.to_dict(orient="records")
    return {"city": city, "count": len(records), "data": records}


# Download endpoint removed for simplified user-facing UI


async def fetch_city_data(
    city: str, days: int = 7, timezone: str = "auto"
) -> pd.DataFrame:
    """Fetch and transform city data directly from API without saving locally."""
    loc = await _geocode_search(city, count=1)
    if not loc:
        raise HTTPException(status_code=404, detail=f"Kota tidak ditemukan: {city}")

    city_info = loc[0]
    lat, lon = city_info["lat"], city_info["lon"]

    # Fetch weather and air quality data
    weather_params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation,relative_humidity_2m,windspeed_10m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "forecast_days": days,
        "timezone": timezone,
    }
    air_params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "pm2_5,pm10",
        "forecast_days": days,
        "timezone": timezone,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            # fetch weather
            weather_resp = await client.get(
                "https://api.open-meteo.com/v1/forecast", params=weather_params
            )
            try:
                weather_resp.raise_for_status()
                weather_data = weather_resp.json()
            except Exception as e:
                raise HTTPException(
                    status_code=502, detail=f"Weather API failed for {city}: {str(e)}"
                )

            # fetch air quality separately; if it fails we continue with empty air data
            air_data = {"hourly": {"time": [], "pm2_5": [], "pm10": []}}
            try:
                air_resp = await client.get(
                    "https://air-quality-api.open-meteo.com/v1/air-quality",
                    params=air_params,
                )
                try:
                    air_resp.raise_for_status()
                    air_data = air_resp.json()
                except Exception:
                    # log full response body for debugging but do not raise
                    try:
                        body = air_resp.text
                    except Exception:
                        body = "<no-body>"
                    import logging

                    logging.getLogger(__name__).warning(
                        "Air quality API returned non-2xx for %s (%s): %s",
                        city,
                        getattr(air_resp, "status_code", "unknown"),
                        body,
                    )
                    # keep air_data as empty structure so downstream merges yield NaN values
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(
                    "Air quality API request failed for %s: %s", city, str(e)
                )
                # leave air_data as empty structure
    except HTTPException:
        # re-raise HTTP exceptions from above
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengambil data: {str(e)}")

    # Transform data to daily format
    daily_weather = pd.DataFrame(
        {
            "date": pd.to_datetime(weather_data["daily"]["time"]),
            "temp_min": weather_data["daily"]["temperature_2m_min"],
            "temp_max": weather_data["daily"]["temperature_2m_max"],
            "total_rain": weather_data["daily"]["precipitation_sum"],
        }
    )

    # Calculate daily averages for air quality
    hourly_air = pd.DataFrame(
        {
            "time": pd.to_datetime(air_data["hourly"]["time"]),
            "pm25": air_data["hourly"].get("pm2_5")
            or air_data["hourly"].get("pm25")
            or [],
            "pm10": air_data["hourly"].get("pm10") or [],
        }
    )
    hourly_air["date"] = hourly_air["time"].dt.date
    daily_air = (
        hourly_air.groupby("date").agg({"pm25": "mean", "pm10": "mean"}).reset_index()
    )
    daily_air["date"] = pd.to_datetime(daily_air["date"])
    # normalize column names expected by frontend
    daily_air = daily_air.rename(columns={"pm25": "pm25_avg", "pm10": "pm10_avg"})

    # Merge weather and air quality data
    daily_data = pd.merge(daily_weather, daily_air, on="date", how="left")
    daily_data["city"] = city

    return daily_data


@app.get("/compare")
async def compare(
    cities: str = Query(..., description="Daftar kota dipisah koma"),
    days: int = Query(
        7, description="Jumlah hari untuk perbandingan (1-16)", ge=1, le=16
    ),
    timezone: str = Query("auto", description="Zona waktu (default: auto)"),
) -> dict:
    city_list: List[str] = [c.strip() for c in cities.split(",") if c.strip()]
    if len(city_list) < 2:
        raise HTTPException(
            status_code=400, detail="Butuh minimal dua kota untuk perbandingan."
        )

    # Fetch data for all cities, but be tolerant: collect failures per-city
    results = []
    failed = []
    for city in city_list:
        try:
            df = await fetch_city_data(city, days, timezone)
            records = df.to_dict(orient="records")
            results.append({"name": city, "daily": records, "error": None})
        except HTTPException as e:
            # keep per-city HTTP error and continue
            failed.append(
                {"city": city, "status": e.status_code, "detail": str(e.detail)}
            )
            results.append({"name": city, "daily": [], "error": str(e.detail)})
        except Exception as e:
            # catch-all: record failure and continue
            failed.append({"city": city, "status": 500, "detail": str(e)})
            results.append({"name": city, "daily": [], "error": str(e)})

    # require at least two successful cities for a meaningful comparison
    success_count = sum(1 for r in results if r.get("daily"))
    if success_count < 2:
        # include failures in the response to help debugging
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Not enough successful city data for comparison",
                "results": results,
                "failed": failed,
            },
        )

    # Combine all successful city data into flattened rows for backward compatibility
    dfs = [pd.DataFrame(r["daily"]) for r in results if r.get("daily")]
    merged = pd.concat(dfs, ignore_index=True)
    records = merged.to_dict(orient="records")

    return {
        "cities": results,
        "count": len(records),
        "days": days,
        "data": records,
        "failed": failed,
    }


def main() -> None:
    # Run uvicorn programmatically for convenience: `etl-weather-web`
    import uvicorn
    import logging

    # General logging setup (let Uvicorn handle its own loggers)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    uvicorn.run(
        "etl_weather.web:app",
        host="localhost",
        port=8000,
        reload=False,
        log_level="info",
    )
