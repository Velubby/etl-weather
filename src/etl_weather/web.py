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


async def fetch_city_data(city: str, days: int = 7, timezone: str = "auto") -> pd.DataFrame:
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
            weather_resp = await client.get("https://api.open-meteo.com/v1/forecast", params=weather_params)
            air_resp = await client.get("https://air-quality-api.open-meteo.com/v1/air-quality", params=air_params)
            
            weather_resp.raise_for_status()
            air_resp.raise_for_status()
            
            weather_data = weather_resp.json()
            air_data = air_resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengambil data: {str(e)}")
    
    # Transform data to daily format
    daily_weather = pd.DataFrame({
        'date': pd.to_datetime(weather_data['daily']['time']),
        'temp_min': weather_data['daily']['temperature_2m_min'],
        'temp_max': weather_data['daily']['temperature_2m_max'],
        'total_rain': weather_data['daily']['precipitation_sum']
    })
    
    # Calculate daily averages for air quality
    hourly_air = pd.DataFrame({
        'time': pd.to_datetime(air_data['hourly']['time']),
        'pm25': air_data['hourly']['pm2_5'],
        'pm10': air_data['hourly']['pm10']
    })
    hourly_air['date'] = hourly_air['time'].dt.date
    daily_air = hourly_air.groupby('date').agg({
        'pm25': 'mean',
        'pm10': 'mean'
    }).reset_index()
    daily_air['date'] = pd.to_datetime(daily_air['date'])
    
    # Merge weather and air quality data
    daily_data = pd.merge(daily_weather, daily_air, on='date', how='left')
    daily_data['city'] = city
    
    return daily_data

@app.get("/compare")
async def compare(
    cities: str = Query(..., description="Daftar kota dipisah koma"),
    days: int = Query(7, description="Jumlah hari untuk perbandingan (1-16)", ge=1, le=16),
    timezone: str = Query("auto", description="Zona waktu (default: auto)"),
) -> dict:
    city_list: List[str] = [c.strip() for c in cities.split(",") if c.strip()]
    if len(city_list) < 2:
        raise HTTPException(
            status_code=400, detail="Butuh minimal dua kota untuk perbandingan."
        )
    
    # Fetch data for all cities concurrently
    dfs = []
    for city in city_list:
        try:
            df = await fetch_city_data(city, days, timezone)
            dfs.append(df)
        except HTTPException as e:
            # Pass through HTTP exceptions with proper status codes
            raise e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error mengambil data untuk {city}: {str(e)}"
            )
    
    # Combine all city data
    if dfs:
        merged = pd.concat(dfs, ignore_index=True)
        records = merged.to_dict(orient="records")
        return {
            "cities": city_list,
            "count": len(records),
            "days": days,
            "data": records
        }
    else:
        raise HTTPException(status_code=500, detail="Gagal mengambil data untuk semua kota")


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
