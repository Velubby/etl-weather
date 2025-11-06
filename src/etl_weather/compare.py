from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
import altair as alt

from .utils import slugify


def _load_daily(city: str) -> pd.DataFrame:
    slug = slugify(city)
    p = Path("data/processed") / f"{slug}_daily.csv"
    if not p.exists():
        raise FileNotFoundError(
            f"CSV tidak ditemukan untuk '{city}': {p}. Jalankan fetch+transform terlebih dahulu."
        )
    df = pd.read_csv(p, parse_dates=["date"])
    df["city"] = city
    # Pastikan tipe numerik
    for col in [
        "temp_min",
        "temp_max",
        "total_rain",
        "pm25_avg",
        "pm10_avg",
        "feels_like_avg",
        "dew_point_avg",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _chart_temp_max(df: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(df, title="Suhu Maksimum Harian per Kota")
        .mark_line(point=True)
        .encode(
            x=alt.X("date:T", title="Tanggal"),
            y=alt.Y("temp_max:Q", title="Suhu Max (°C)"),
            color=alt.Color("city:N", title="Kota"),
            tooltip=["date:T", "city:N", alt.Tooltip("temp_max:Q", format=".1f")],
        )
        .properties(height=250)
        .interactive()
    )


def _chart_pm25(df: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(df, title="PM2.5 Rata-rata Harian per Kota")
        .mark_line(point=True, color="crimson")
        .encode(
            x=alt.X("date:T", title="Tanggal"),
            y=alt.Y("pm25_avg:Q", title="PM2.5 (µg/m³)"),
            color=alt.Color("city:N", title="Kota"),
            tooltip=["date:T", "city:N", alt.Tooltip("pm25_avg:Q", format=".1f")],
        )
        .properties(height=250)
        .interactive()
    )


def run(cities: Iterable[str], output: Optional[str] = None) -> str:
    cities_list: List[str] = list(cities)
    if len(cities_list) < 2:
        raise ValueError("Butuh minimal 2 kota untuk perbandingan.")
    frames = [_load_daily(c) for c in cities_list]
    df = pd.concat(frames, ignore_index=True)

    # Build charts
    c1 = _chart_temp_max(df)
    c2 = _chart_pm25(df)
    charts = [c1, c2]

    # Save simple HTML page combining charts
    html_parts = [c.to_html() for c in charts]
    html = (
        "<!doctype html><meta charset='utf-8'><title>Perbandingan Kota</title>"
        + "<h1>Perbandingan Kota: "
        + ", ".join(cities_list)
        + "</h1>"
        + "".join(html_parts)
    )

    out = (
        Path(output)
        if output
        else Path("reports")
        / f"compare_{'-'.join(slugify(c) for c in cities_list)}.html"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return str(out)
