from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import altair as alt
import pandas as pd

# Atasi limit default Altair (5000 baris); data kita kecil, tapi set untuk amankan
alt.data_transformers.disable_max_rows()


def _load_df(csv_path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, parse_dates=["date"])
    # Pastikan tipe numerik agar skala grafik benar
    for col in ["temp_min", "temp_max", "total_rain", "pm25_avg", "pm10_avg"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def chart_temp(df: pd.DataFrame) -> alt.Chart:
    # Ubah ke format long agar bisa dua garis (min & max)
    temp_long = df.melt(
        id_vars=["date"],
        value_vars=["temp_min", "temp_max"],
        var_name="metric",
        value_name="value",
    )
    title = "Suhu Harian (Min & Max)"
    c = (
        alt.Chart(temp_long, title=title)
        .mark_line(point=True)
        .encode(
            x=alt.X("date:T", title="Tanggal"),
            y=alt.Y("value:Q", title="Suhu (°C)"),
            color=alt.Color("metric:N", title="Metrik", sort=["temp_min", "temp_max"]),
            tooltip=[
                alt.Tooltip("date:T", title="Tanggal"),
                alt.Tooltip("metric:N", title="Metrik"),
                alt.Tooltip("value:Q", title="Suhu (°C)", format=".1f"),
            ],
        )
        .properties(height=250)
        .interactive()
    )
    return c


def chart_rain(df: pd.DataFrame) -> alt.Chart:
    title = "Total Hujan Harian"
    c = (
        alt.Chart(df, title=title)
        .mark_bar(color="#4c78a8")
        .encode(
            x=alt.X("date:T", title="Tanggal"),
            y=alt.Y("total_rain:Q", title="Hujan (mm)"),
            tooltip=[
                alt.Tooltip("date:T", title="Tanggal"),
                alt.Tooltip("total_rain:Q", title="Hujan (mm)", format=".1f"),
            ],
        )
        .properties(height=250)
        .interactive()
    )
    return c


def chart_pm25(df: pd.DataFrame) -> alt.LayerChart:
    title = "PM2.5 Rata-rata Harian"
    base = alt.Chart(df, title=title).encode(x=alt.X("date:T", title="Tanggal"))

    # Garis ambang sederhana (EPA): 12 (Baik/Sedang), 35.4 (Sedang/Tidak Sehat bagi Sensitif)
    rule_12 = (
        alt.Chart(pd.DataFrame({"y": [12]}))
        .mark_rule(color="#2ca02c", strokeDash=[4, 4])
        .encode(y="y:Q")
    )
    rule_354 = (
        alt.Chart(pd.DataFrame({"y": [35.4]}))
        .mark_rule(color="#d62728", strokeDash=[4, 4])
        .encode(y="y:Q")
    )

    line = (
        base.mark_line(color="crimson", point=True)
        .encode(
            y=alt.Y("pm25_avg:Q", title="PM2.5 (µg/m³)"),
            tooltip=[
                alt.Tooltip("date:T", title="Tanggal"),
                alt.Tooltip("pm25_avg:Q", title="PM2.5", format=".1f"),
            ],
        )
        .properties(height=250)
        .interactive()
    )
    return alt.layer(line, rule_12, rule_354)


def build_charts(csv_path: str | Path) -> Tuple[alt.Chart, alt.Chart, alt.Chart]:
    df = _load_df(csv_path)
    c_temp = chart_temp(df)
    c_rain = chart_rain(df)
    c_pm25 = chart_pm25(df)
    return c_temp, c_rain, c_pm25


def charts_to_html(charts: List[alt.Chart]) -> List[str]:
    # to_html menyertakan runtime Vega-Lite sehingga bisa di-embed langsung di laporan
    return [c.to_html() for c in charts]


def save_charts_html(charts: List[alt.Chart], out_dir: str | Path) -> List[str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: List[str] = []
    for i, c in enumerate(charts, start=1):
        p = out / f"chart_{i}.html"
        c.save(p)  # simpan sebagai HTML
        paths.append(str(p))
    return paths
