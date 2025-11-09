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
    # Calculate daily average temperature
    df['temp_avg'] = (df['temp_min'] + df['temp_max']) / 2
    
    # Create base chart
    title = "Suhu Harian (Minimum & Maksimum)"
    base = alt.Chart(df, title=alt.TitleParams(title, fontSize=16, anchor="middle"))
    
    # Create area between min and max
    area = base.mark_area(opacity=0.3, color="#3182bd").encode(
        x=alt.X("date:T", title="Tanggal", axis=alt.Axis(labelAngle=-45, grid=True)),
        y=alt.Y("temp_min:Q", title="Suhu (°C)", scale=alt.Scale(zero=False)),
        y2="temp_max:Q",
        tooltip=[
            alt.Tooltip("date:T", title="Tanggal", format="%Y-%m-%d"),
            alt.Tooltip("temp_min:Q", title="Suhu Min (°C)", format=".1f"),
            alt.Tooltip("temp_max:Q", title="Suhu Max (°C)", format=".1f"),
            alt.Tooltip("temp_avg:Q", title="Suhu Rata-rata (°C)", format=".1f"),
        ]
    )
    
    # Add lines for min and max
    lines = base.mark_line(strokeWidth=2).encode(
        x="date:T",
        y=alt.Y("temp_max:Q", title="Suhu (°C)"),
        color=alt.value("#ff7f0e")
    ) + base.mark_line(strokeWidth=2).encode(
        x="date:T",
        y="temp_min:Q",
        color=alt.value("#1f77b4")
    )
    
    # Add points
    points = base.mark_circle(size=50).encode(
        x="date:T",
        y="temp_max:Q",
        color=alt.value("#ff7f0e")
    ) + base.mark_circle(size=50).encode(
        x="date:T",
        y="temp_min:Q",
        color=alt.value("#1f77b4")
    )
    
    # Combine all layers
    c = (alt.layer(area, lines, points)
        .properties(height=300, width="container")
        .configure_axis(labelFontSize=12, titleFontSize=14, grid=True)
        .configure_view(strokeWidth=0)
        .interactive()
    )
    return c


def chart_rain(df: pd.DataFrame) -> alt.Chart:
    # Calculate moving average for reference line
    df['rain_ma7'] = df['total_rain'].rolling(window=7).mean()
    
    title = "Total Curah Hujan Harian"
    base = alt.Chart(df, title=alt.TitleParams(title, fontSize=16, anchor="middle"))
    
    # Create gradient color scale based on rainfall intensity
    bars = base.mark_bar().encode(
        x=alt.X("date:T", title="Tanggal", axis=alt.Axis(labelAngle=-45, grid=True)),
        y=alt.Y("total_rain:Q", title="Curah Hujan (mm)"),
        color=alt.Color(
            "total_rain:Q",
            scale=alt.Scale(
                domain=[0, 5, 20, 50, 100],
                range=["#c6dbef", "#9ecae1", "#6baed6", "#3182bd", "#08519c"]
            ),
            legend=alt.Legend(title="Intensitas Hujan (mm)")
        ),
        tooltip=[
            alt.Tooltip("date:T", title="Tanggal", format="%Y-%m-%d"),
            alt.Tooltip("total_rain:Q", title="Curah Hujan", format=".1f"),
            alt.Tooltip("rain_ma7:Q", title="Rata-rata 7 Hari", format=".1f")
        ]
    )
    
    # Add 7-day moving average line
    line = base.mark_line(
        color="red",
        strokeWidth=2,
        strokeDash=[4, 4]
    ).encode(
        x="date:T",
        y="rain_ma7:Q",
        tooltip=[
            alt.Tooltip("rain_ma7:Q", title="Rata-rata 7 Hari", format=".1f")
        ]
    )
    
    # Combine layers
    c = (alt.layer(bars, line)
        .properties(height=300, width="container")
        .configure_axis(labelFontSize=12, titleFontSize=14, grid=True)
        .configure_view(strokeWidth=0)
        .interactive()
    )
    return c


def chart_pm25(df: pd.DataFrame) -> alt.LayerChart:
    # Add air quality categories
    def get_aqi_status(val):
        if pd.isna(val):
            return "Tidak ada data"
        elif val <= 12:
            return "Baik"
        elif val <= 35.4:
            return "Sedang"
        else:
            return "Tidak Sehat"
    
    df['aqi_status'] = df['pm25_avg'].apply(get_aqi_status)
    
    title = "Rata-rata PM2.5 Harian dan Kategori Kualitas Udara"
    base = alt.Chart(df, title=alt.TitleParams(title, fontSize=16, anchor="middle"))

    # Create background bands for AQI levels
    band_df = pd.DataFrame([
        {"level": "Baik", "start": 0, "end": 12, "color": "#2ca02c"},
        {"level": "Sedang", "start": 12, "end": 35.4, "color": "#ffbb78"},
        {"level": "Tidak Sehat", "start": 35.4, "end": 100, "color": "#d62728"}
    ])
    
    bands = alt.Chart(band_df).mark_rect(opacity=0.2).encode(
        y=alt.Y('start:Q', title="PM2.5 (µg/m³)"),
        y2=alt.Y2('end:Q'),
        color=alt.Color(
            'level:N',
            scale=alt.Scale(
                domain=["Baik", "Sedang", "Tidak Sehat"],
                range=["#2ca02c", "#ffbb78", "#d62728"]
            ),
            legend=alt.Legend(title="Kategori Kualitas Udara")
        )
    )

    # Main line
    line = base.mark_line(strokeWidth=2).encode(
        x=alt.X("date:T", title="Tanggal", axis=alt.Axis(labelAngle=-45, grid=True)),
        y=alt.Y("pm25_avg:Q", title="PM2.5 (µg/m³)", scale=alt.Scale(zero=True)),
        color=alt.Color(
            "aqi_status:N",
            scale=alt.Scale(
                domain=["Baik", "Sedang", "Tidak Sehat"],
                range=["#2ca02c", "#ffbb78", "#d62728"]
            ),
            legend=None
        )
    )

    # Points with tooltips
    points = base.mark_circle(size=60).encode(
        x="date:T",
        y="pm25_avg:Q",
        color=alt.Color(
            "aqi_status:N",
            scale=alt.Scale(
                domain=["Baik", "Sedang", "Tidak Sehat"],
                range=["#2ca02c", "#ffbb78", "#d62728"]
            ),
            legend=None
        ),
        tooltip=[
            alt.Tooltip("date:T", title="Tanggal", format="%Y-%m-%d"),
            alt.Tooltip("pm25_avg:Q", title="PM2.5", format=".1f"),
            alt.Tooltip("aqi_status:N", title="Status Kualitas Udara")
        ]
    )

    # Combine all layers
    c = (alt.layer(bands, line, points)
        .properties(height=300, width="container")
        .configure_axis(labelFontSize=12, titleFontSize=14, grid=True)
        .configure_view(strokeWidth=0)
        .interactive()
    )
    return c


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
