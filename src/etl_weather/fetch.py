from __future__ import annotations
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional
import httpx
from .utils import geocode_city, slugify

LOG = logging.getLogger(__name__)
RAW_DIR = Path("data") / "raw"
SAMPLES_DIR = Path("data") / "samples"
RAW_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "etl-weather/0.1 (student project; https://open-meteo.com/)"}


class NetworkError(RuntimeError): ...


def _request_json(
    url: str, params: Dict[str, Any], retries: int = 3, timeout: int = 10
) -> Dict[str, Any]:
    delay = 0.8
    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            with httpx.Client(timeout=timeout, headers=HEADERS) as c:
                resp = c.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            last_exc = exc
            LOG.warning("HTTP error (attempt %d/%d) %s: %s", attempt, retries, url, exc)
            time.sleep(delay)
            delay *= 1.6
    raise NetworkError(f"Gagal mengambil {url}: {last_exc}")


def _save_json(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    LOG.info("Saved %s", path)


def _fetch_weather_air(
    lat: float, lon: float, days: int, timezone: str
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    weather_params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation",
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
    weather = _request_json("https://api.open-meteo.com/v1/forecast", weather_params)
    air = _request_json(
        "https://air-quality-api.open-meteo.com/v1/air-quality", air_params
    )
    return weather, air


def _load_sample(
    slug: str, sample_dir: Optional[str] = None
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    sdir = Path(sample_dir) if sample_dir else SAMPLES_DIR
    w = sdir / f"{slug}_weather.json"
    a = sdir / f"{slug}_air.json"
    if not w.exists() or not a.exists():
        raise FileNotFoundError(
            f"Sample tidak ditemukan di {sdir}. Pastikan {w.name} & {a.name} ada."
        )
    weather = json.loads(w.read_text(encoding="utf-8"))
    air = json.loads(a.read_text(encoding="utf-8"))
    return weather, air


def run(
    city: str,
    days: int = 7,
    timezone: Optional[str] = None,
    *,
    offline: bool = False,
    sample_dir: Optional[str] = None,
    fallback: bool = True,
) -> Dict[str, str]:
    """Ambil data cuaca & kualitas udara lalu simpan ke data/raw.
    - offline=True: pakai sample di data/samples
    - fallback=True: jika jaringan gagal, pakai sample bila tersedia
    """
    if days < 1 or days > 16:
        raise ValueError("days harus 1-16 untuk Open-Meteo")
    slug = slugify(city)
    ts = time.strftime("%Y%m%dT%H%M%S")
    weather_ts = RAW_DIR / f"{slug}_weather_{ts}.json"
    air_ts = RAW_DIR / f"{slug}_air_{ts}.json"
    weather_latest = RAW_DIR / f"{slug}_weather.json"
    air_latest = RAW_DIR / f"{slug}_air.json"

    if offline:
        LOG.info("Mode offline: menggunakan sample untuk '%s'", city)
        weather, air = _load_sample(slug, sample_dir)
    else:
        loc = geocode_city(city)
        tz = timezone or loc.get("timezone") or "auto"
        LOG.info(
            "Geocoded '%s' -> (lat=%.4f, lon=%.4f, tz=%s)",
            loc["name"],
            loc["lat"],
            loc["lon"],
            tz,
        )
        try:
            weather, air = _fetch_weather_air(loc["lat"], loc["lon"], days, tz)
        except Exception as e:
            if fallback:
                LOG.warning("Fetch gagal (%s). Coba pakai sample.", e)
                weather, air = _load_sample(slug, sample_dir)
            else:
                raise

    _save_json(weather, weather_ts)
    _save_json(air, air_ts)
    _save_json(weather, weather_latest)
    _save_json(air, air_latest)
    return {
        "location_name": city,
        "weather_path": str(weather_ts),
        "air_path": str(air_ts),
        "weather_latest": str(weather_latest),
        "air_latest": str(air_latest),
    }
