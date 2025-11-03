from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd
import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from . import fetch as fetch_mod
from . import transform as transform_mod
from .utils import slugify


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
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


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
