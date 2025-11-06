from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd
import httpx
try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - optional dependency
    genai = None
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from . import fetch as fetch_mod
from . import transform as transform_mod
from .utils import slugify



# Initialize Gemini API (optional)
gemini_model = None
if genai is None:
    print("google.generativeai not available; Gemini integration disabled.")
else:
    try:
        if hasattr(genai, "configure") and settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)

        # Print available Gemini models for debugging if supported
        try:
            if hasattr(genai, "list_models"):
                models = genai.list_models()
                print("Available Gemini models:")
                for m in models:
                    print(f"- {getattr(m, 'name', m)} | Supported methods: {getattr(m, 'supported_generation_methods', None)}")
        except Exception as e:
            print(f"Failed to list Gemini models: {str(e)}")

        # Create a client-side model instance only if the client exposes it
        if hasattr(genai, "GenerativeModel") and settings.gemini_api_key:
            try:
                gemini_model = genai.GenerativeModel("models/gemini-2.5-flash")
                # quick smoke test if generate_content present
                if hasattr(gemini_model, "generate_content"):
                    try:
                        resp = gemini_model.generate_content("Simple test message")
                        print("Gemini API Test:", getattr(resp, "text", resp))
                        print("Gemini API initialized successfully!")
                    except Exception as e:
                        print(f"Failed to initialize Gemini model instance: {e}")
                        gemini_model = None
            except Exception as e:
                print(f"Failed to create GenerativeModel instance: {e}")
        else:
            # functional API may still be available (genai.generate_text / genai.generate)
            print("google.generativeai present but GenerativeModel not found; will attempt functional API calls at runtime if configured.")
    except Exception as e:
        print(f"Failed to configure Gemini API: {e}")
        gemini_model = None
import random

# Local fallback fun facts used when Gemini API isn't configured or fails.
# Keep short, friendly facts in Indonesian.
FALLBACK_FUNFACTS = [
    "Tahukah kamu? Kota ini punya pasar tradisional yang sudah berumur ratusan tahun.",
    "Tahukah kamu? Ada festival tahunan di kota ini yang menarik ribuan pengunjung.",
    "Tahukah kamu? Kota ini terkenal dengan makanan jalanannya yang unik dan lezat.",
    "Tahukah kamu? Sungai utama di kota ini pernah menjadi jalur perdagangan penting.",
    "Tahukah kamu? Ada gedung bersejarah di kota ini yang menjadi ikon arsitektur lokal.",
]

# Note: templates/static may not be available in test env (jinja2 missing);
# initialize them defensively so unit tests don't fail when optional deps
# are not installed.


_funfact_cache: dict[str, tuple[float, dict]] = {}
FUNFACT_TTL = 6 * 60 * 60  # 6 hours


def _get_city_funfact(city: str, weather_data: dict | None = None) -> dict:
    """Generate a city-focused fun fact using Gemini. If weather_data is
    available, include a short contextual mention about the current
    conditions; otherwise just return an interesting city fact.
    """
    global gemini_model, _funfact_cache

    # cache key
    key = (city or '__random__').lower()
    now = __import__('time').time()

    # check cache
    cached = _funfact_cache.get(key)
    if cached:
        ts, payload = cached
        if now - ts < FUNFACT_TTL:
            resp = dict(payload)
            resp['cached'] = True
            return resp

    # If Gemini not available, use fallback facts
    if not gemini_model:
        try:
            fact = random.choice(FALLBACK_FUNFACTS)
            if weather_data and weather_data.get('temperature') != 'N/A':
                temp = weather_data.get('temperature')
                if temp is not None:
                    fact = f"{fact} Saat ini sekitar {temp}°C."
            payload = {'city': city, 'city_funfact': fact, 'cached': False, 'source': 'fallback'}
            _funfact_cache[key] = (now, payload)
            return dict(payload)
        except Exception:
            return {'city': city, 'city_funfact': 'Fun facts are not available (Gemini API not initialized)', 'cached': False, 'source': 'none'}

    def _call_gemini(prompt: str) -> str | None:
        """Try several possible client call patterns to obtain text from Gemini client.
        Returns a string on success or None on failure/unsupported.
        """
        # 1) If we have an instantiated model object with generate_content
        try:
            if gemini_model and hasattr(gemini_model, "generate_content"):
                resp = gemini_model.generate_content(prompt)
                if hasattr(resp, "text"):
                    return resp.text.strip()
                if isinstance(resp, dict):
                    return resp.get("text") or resp.get("output")
        except Exception as e:
            print(f"Gemini instance generate_content error: {e}")

        # 2) Functional genai.generate_text(model=..., input=...) or genai.generate
        if genai:
            try:
                # try generate_text
                if hasattr(genai, "generate_text"):
                    # some clients accept `input` or `prompt`
                    try:
                        r = genai.generate_text(model="models/gemini-2.5-flash", input=prompt)
                    except TypeError:
                        r = genai.generate_text(model="models/gemini-2.5-flash", prompt=prompt)
                    if isinstance(r, dict):
                        return r.get("text") or r.get("output")
                    if hasattr(r, "text"):
                        return r.text

                # try generic generate (newer clients)
                if hasattr(genai, "generate"):
                    try:
                        r = genai.generate(model="models/gemini-2.5-flash", prompt=prompt)
                    except TypeError:
                        r = genai.generate(model="models/gemini-2.5-flash", input=prompt)
                    # extract text from possible response shapes
                    if isinstance(r, dict):
                        # check common shapes
                        if "candidates" in r and isinstance(r["candidates"], list) and r["candidates"]:
                            return r["candidates"][0].get("content") or r["candidates"][0].get("text")
                        return r.get("text") or r.get("output")
                    if hasattr(r, "text"):
                        return r.text
            except Exception as e:
                print(f"Functional genai call error: {e}")

        return None

    # Build prompt for Gemini
    try:
        if weather_data:
            prompt = f"""City: {city}
Current conditions:
- Temperature: {weather_data.get('temperature', 'N/A')}°C
- Humidity: {weather_data.get('humidity', 'N/A')}%
- Description: {weather_data.get('weather_description', 'N/A')}

Berikan satu fun fact menarik tentang kota {city} dalam maksimal 2 kalimat. Jika relevan, kamu boleh mengaitkannya singkat dengan kondisi cuaca saat ini."""
        else:
            prompt = f"Berikan satu fun fact menarik tentang kota {city} dalam maksimal 2 kalimat. Buatlah dalam bahasa Indonesia dan pastikan fakta tersebut menarik dan menghibur."

        # Try multiple client patterns via helper
        text = _call_gemini(prompt)
        if not text:
            print("Gemini response object: no text returned or client unsupported")
            text = "Could not generate fun fact at this time"

        payload = {'city': city, 'city_funfact': text, 'cached': False, 'source': 'gemini'}
        _funfact_cache[key] = (now, payload)
        return payload
    except Exception as e:
        import traceback
        print(f"Fun fact generation error: {str(e)}")
        traceback.print_exc()
        return {'city': city, 'city_funfact': 'Could not generate fun fact at this time', 'cached': False, 'source': 'error'}


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
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        j = r.json()
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

WEB_DIR = Path(__file__).parent / "webui"
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"
try:
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
except Exception as e:  # pragma: no cover - optional runtime
    print(f"Templates/static not initialized (optional): {e}")
    templates = None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    # If Jinja2 templates aren't available (e.g., in lightweight test env),
    # return a simple HTML fallback so the app still responds.
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return HTMLResponse("<html><body><h1>ETL Weather API</h1><p>UI not available (templates missing)</p></body></html>")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/city-funfact")
async def get_city_funfact(city: str) -> dict:
    try:
        p = _ensure_daily(city, False)
        df = _load_csv(p)
        if len(df) == 0:
            raise HTTPException(status_code=404, detail="No weather data found")
            
        # Get the most recent weather data
        latest = df.iloc[-1]
        
        # Debug logging
        columns = df.columns.tolist()
        print("Available columns:", columns)
        print("Latest data:", latest.to_dict())
        
        # Extract weather data
        weather_data = {}
        
        # Find temperature (look for various possible column names)
        for temp_col in ['temperature', 'temperature_2m', 'temp']:
            if temp_col in columns:
                weather_data['temperature'] = latest[temp_col]
                break
                
        # Find humidity
        for humid_col in ['humidity', 'relative_humidity_2m', 'humidity_2m']:
            if humid_col in columns:
                weather_data['humidity'] = latest[humid_col]
                break
                
        # Find weather description
        for weather_col in ['weather_code', 'weather', 'description']:
            if weather_col in columns:
                weather_data['weather_description'] = latest[weather_col]
                break
        
        # Add defaults if values are missing
        weather_data.setdefault('temperature', 'N/A')
        weather_data.setdefault('humidity', 'N/A')
        weather_data.setdefault('weather_description', 'N/A')
        
        print("Extracted weather data:", weather_data)

        # Generate the city-focused funfact (optionally referencing weather)
        fun_fact = _get_city_funfact(city, weather_data)
        # _get_city_funfact returns a structured payload dict with keys
        # like 'city_funfact', 'source' and 'cached'. Ensure the HTTP
        # response is a flat mapping where 'city_funfact' is a string
        # (this matches the tests and the web UI expectations).
        if isinstance(fun_fact, dict):
            return fun_fact
        # Fallback if implementation returns a plain string
        return {"city_funfact": str(fun_fact), "source": "unknown", "cached": False}

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Weather data not found for this city"
        )
    except Exception as e:
        print(f"Error in fun fact endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating fun fact: {str(e)}"
        )


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


@app.get("/compare")
async def compare(
    cities: str = Query(..., description="Daftar kota dipisah koma"),
    refresh: bool = False,
) -> dict:
    city_list: List[str] = [c.strip() for c in cities.split(",") if c.strip()]
    if len(city_list) < 2:
        raise HTTPException(
            status_code=400, detail="Butuh minimal dua kota untuk perbandingan."
        )
    frames: List[pd.DataFrame] = []
    for c in city_list:
        p = _ensure_daily(c, refresh)
        df = _load_csv(p)
        df["city"] = c
        frames.append(df)
    merged = pd.concat(frames, ignore_index=True)
    records = merged.to_dict(orient="records")
    return {"cities": city_list, "count": len(records), "data": records}


def main() -> None:
    # Run uvicorn programmatically for convenience: `etl-weather-web`
    import uvicorn

    uvicorn.run(
        "etl_weather.web:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
