from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

from .utils import slugify

LOG = logging.getLogger(__name__)
RAW_DIR = Path("data") / "raw"
PROC_DIR = Path("data") / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)


def _safe_hourly_frame(hourly: dict, fields: List[str]) -> pd.DataFrame:
    """Bangun DataFrame dari blok 'hourly' dengan penjagaan panjang list.
    Jika ada kolom yang hilang atau panjang tidak cocok, diisi None."""
    times: List[str] = hourly.get("time", []) or []
    data = {"time": times}
    n = len(times)
    for col in fields:
        vals = hourly.get(col, [])
        if not isinstance(vals, list) or len(vals) != n:
            vals = [None] * n
        data[col] = vals
    return pd.DataFrame(data)


def _categorize_pm25(value: Optional[float]) -> str:
    """Kategori sederhana berdasarkan konsentrasi PM2.5 (µg/m³).
    Catatan: ini bukan perhitungan AQI penuh, hanya klasifikasi kasar."""
    if value is None or pd.isna(value):
        return "Tidak diketahui"
    v = float(value)
    if v <= 12:
        return "Baik"
    if v <= 35.4:
        return "Sedang"
    if v <= 55.4:
        return "Tidak sehat (sensitif)"
    if v <= 150.4:
        return "Tidak sehat"
    if v <= 250.4:
        return "Sangat tidak sehat"
    return "Berbahaya"


def run(city: str, out_path: Optional[str] = None) -> str:
    """Transform: gabungkan cuaca+udara per jam -> agregasi harian -> simpan CSV."""
    slug = slugify(city)
    weather_path = RAW_DIR / f"{slug}_weather.json"
    air_path = RAW_DIR / f"{slug}_air.json"

    if not weather_path.exists() or not air_path.exists():
        raise FileNotFoundError(
            f"File raw belum tersedia untuk '{city}'. Jalankan dulu: etl-weather fetch --city \"{city}\""
        )

    # Load JSON
    weather = json.loads(weather_path.read_text(encoding="utf-8"))
    air = json.loads(air_path.read_text(encoding="utf-8"))

    # Build hourly frames dengan penjagaan panjang
    hw = _safe_hourly_frame(
        weather.get("hourly", {}), ["temperature_2m", "precipitation"]
    )
    ha = _safe_hourly_frame(air.get("hourly", {}), ["pm2_5", "pm10"])

    # Rename kolom ke nama ringkas
    hw = hw.rename(columns={"temperature_2m": "temp", "precipitation": "rain"})
    ha = ha.rename(columns={"pm2_5": "pm25", "pm10": "pm10"})

    # Merge dan tipe data
    df = pd.merge(hw, ha, on="time", how="outer").sort_values("time", ignore_index=True)
    # Konversi tipe numeric aman
    for col in ["temp", "rain", "pm25", "pm10"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # Waktu -> tanggal
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df["date"] = df["time"].dt.date

    # Hapus baris tanpa date valid
    df = df.dropna(subset=["date"])

    # Agregasi harian dari data per jam
    daily = (
        df.groupby("date", dropna=False)
        .agg(
            temp_min=("temp", "min"),
            temp_max=("temp", "max"),
            total_rain=("rain", "sum"),
            pm25_avg=("pm25", "mean"),
            pm10_avg=("pm10", "mean"),
        )
        .reset_index()
        .sort_values("date")
    )

    # Bersihkan nilai: hujan NaN -> 0, bulatkan
    daily["total_rain"] = daily["total_rain"].fillna(0.0)
    daily[["temp_min", "temp_max", "total_rain", "pm25_avg", "pm10_avg"]] = daily[
        ["temp_min", "temp_max", "total_rain", "pm25_avg", "pm10_avg"]
    ].round(2)

    # Tambah kategori PM2.5
    daily["pm25_category"] = [_categorize_pm25(v) for v in daily["pm25_avg"].tolist()]

    # Gabungkan informasi harian dari API (sunrise/sunset, jika tersedia)
    w_daily = weather.get("daily", {}) if isinstance(weather, dict) else {}
    if isinstance(w_daily, dict) and (
        w_daily.get("time") or w_daily.get("sunrise") or w_daily.get("sunset")
    ):
        # Bangun frame harian aman untuk sunrise/sunset
        times = w_daily.get("time", []) or []
        n = len(times)

        def _fit(vals):
            vals = vals or []
            return vals if isinstance(vals, list) and len(vals) == n else [None] * n

        dapi = pd.DataFrame(
            {
                "date": pd.to_datetime(times, errors="coerce").date,
                "sunrise": _fit(w_daily.get("sunrise")),
                "sunset": _fit(w_daily.get("sunset")),
            }
        )
        dapi = dapi.dropna(subset=["date"])  # buang baris tanpa tanggal
        # Merge kiri agar kolom tambahan muncul bila cocok
        daily = daily.merge(dapi, on="date", how="left")

    # Simpan
    out_file = Path(out_path) if out_path else PROC_DIR / f"{slug}_daily.csv"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(out_file, index=False)
    LOG.info("Saved daily aggregates -> %s", out_file)

    return str(out_file)


def run_hourly(city: str, out_path: Optional[str] = None) -> str:
    """Transform: gabungkan cuaca + udara per jam -> simpan CSV hourly.

    Kolom yang dihasilkan bersifat best-effort:
    - Wajib: time, temp, rain, pm25, pm10
    - Opsional (jika tersedia di sumber): rh (kelembaban %), wind (km/jam),
      feels_like (apparent_temperature), wcode (weather_code), date
    """
    slug = slugify(city)
    weather_path = RAW_DIR / f"{slug}_weather.json"
    air_path = RAW_DIR / f"{slug}_air.json"

    if not weather_path.exists() or not air_path.exists():
        raise FileNotFoundError(
            f"File raw belum tersedia untuk '{city}'. Jalankan dulu: etl-weather fetch --city \"{city}\""
        )

    # Load JSON
    weather = json.loads(weather_path.read_text(encoding="utf-8"))
    air = json.loads(air_path.read_text(encoding="utf-8"))

    # Siapkan kolom hourly yang mungkin tersedia
    hw = _safe_hourly_frame(
        weather.get("hourly", {}),
        [
            "temperature_2m",
            "precipitation",
            "relative_humidity_2m",
            "wind_speed_10m",
            "apparent_temperature",
            "weather_code",
        ],
    )
    ha = _safe_hourly_frame(air.get("hourly", {}), ["pm2_5", "pm10"])

    # Rename kolom ringkas
    hw = hw.rename(
        columns={
            "temperature_2m": "temp",
            "precipitation": "rain",
            "relative_humidity_2m": "rh",
            "wind_speed_10m": "wind",
            "apparent_temperature": "feels_like",
            "weather_code": "wcode",
        }
    )
    ha = ha.rename(columns={"pm2_5": "pm25", "pm10": "pm10"})

    # Merge
    df = pd.merge(hw, ha, on="time", how="outer").sort_values("time", ignore_index=True)

    # Tipe data aman
    numeric_cols = [
        c
        for c in ["temp", "rain", "rh", "wind", "feels_like", "pm25", "pm10"]
        if c in df.columns
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Konversi waktu & tambah tanggal untuk kemudahan
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"]).reset_index(drop=True)
    df["date"] = df["time"].dt.date

    # Simpan
    out_file = Path(out_path) if out_path else PROC_DIR / f"{slug}_hourly.csv"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_file, index=False)
    LOG.info("Saved hourly data -> %s", out_file)
    return str(out_file)
