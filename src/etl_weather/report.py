from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template

from .utils import slugify
from .viz import build_charts, charts_to_html

LOG = logging.getLogger(__name__)

TPL_DIR = Path(__file__).parent / "templates"
TPL_FILE = TPL_DIR / "report.html"


def _ensure_template_exists() -> None:
    # Jika template belum dibuat, beri peringatan agar dibuat via repo (Day 5 langkah 1)
    if not TPL_FILE.exists():
        LOG.warning(
            "Template tidak ditemukan di %s. Menggunakan template bawaan minimal.",
            TPL_FILE,
        )


def _simple_recommendation(max_temp: float, pm25_avg: float, rainy_days: int) -> str:
    tips = []
    if pm25_avg is not None:
        if pm25_avg > 55.4:
            tips.append(
                "Kualitas udara buruk. Gunakan masker saat di luar, batasi aktivitas outdoor."
            )
        elif pm25_avg > 35.4:
            tips.append(
                "Kualitas udara sedang–buruk bagi kelompok sensitif. Kurangi paparan di luar."
            )
    if max_temp is not None and max_temp > 33:
        tips.append(
            "Cuaca panas. Hindari aktivitas berat siang hari dan perbanyak minum."
        )
    if rainy_days >= 3:
        tips.append(
            "Beberapa hari hujan. Siapkan jas hujan/penutup barang jika beraktivitas di luar."
        )
    return (
        " ".join(tips) or "Kondisi relatif aman. Tetap pantau perubahan cuaca harian."
    )


def _pm25_category(avg_pm25: float) -> str:
    if avg_pm25 is None or pd.isna(avg_pm25):
        return "Tidak diketahui"
    v = float(avg_pm25)
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


def run(city: str, output: Optional[str] = None, csv_path: Optional[str] = None) -> str:
    """Bangun laporan HTML untuk sebuah kota dari CSV agregat harian."""
    slug = slugify(city)
    csv = Path(csv_path) if csv_path else Path("data/processed") / f"{slug}_daily.csv"
    if not csv.exists():
        raise FileNotFoundError(
            f"CSV tidak ditemukan: {csv}. Jalankan transform terlebih dahulu."
        )

    df = pd.read_csv(csv, parse_dates=["date"])

    # Ringkasan metrik
    start = df["date"].min().date() if not df.empty else None
    end = df["date"].max().date() if not df.empty else None
    max_temp = (
        float(df["temp_max"].max())
        if "temp_max" in df.columns and not df["temp_max"].isna().all()
        else None
    )
    min_temp = (
        float(df["temp_min"].min())
        if "temp_min" in df.columns and not df["temp_min"].isna().all()
        else None
    )
    wettest_idx = (
        int(df["total_rain"].idxmax())
        if "total_rain" in df.columns and not df["total_rain"].isna().all()
        else None
    )
    wettest_date = (
        df.loc[wettest_idx, "date"].date() if wettest_idx is not None else None
    )
    wettest_rain = (
        float(df.loc[wettest_idx, "total_rain"]) if wettest_idx is not None else 0.0
    )
    pm25_avg = float(df["pm25_avg"].mean()) if "pm25_avg" in df.columns else None
    feels_like_avg = (
        float(df["feels_like_avg"].mean())
        if "feels_like_avg" in df.columns and not df["feels_like_avg"].isna().all()
        else None
    )
    dew_point_avg = (
        float(df["dew_point_avg"].mean())
        if "dew_point_avg" in df.columns and not df["dew_point_avg"].isna().all()
        else None
    )
    rainy_days = int((df["total_rain"] > 0).sum()) if "total_rain" in df.columns else 0
    pm25_cat = _pm25_category(pm25_avg if pm25_avg is not None else float("nan"))

    # Sunrise/Sunset ringkas (opsional bila tersedia)
    sunrise_earliest = None
    sunset_latest = None
    if "sunrise" in df.columns and not df["sunrise"].isna().all():
        try:
            sunrise_earliest = pd.to_datetime(df["sunrise"], errors="coerce").min()
        except Exception:
            sunrise_earliest = None
    if "sunset" in df.columns and not df["sunset"].isna().all():
        try:
            sunset_latest = pd.to_datetime(df["sunset"], errors="coerce").max()
        except Exception:
            sunset_latest = None

    # Grafik (Altair)
    charts = list(build_charts(csv))
    charts_html = charts_to_html(charts)

    # Rekomendasi
    recommendation = _simple_recommendation(
        max_temp or 0.0, pm25_avg or 0.0, rainy_days
    )

    # Render template
    _ensure_template_exists()
    if TPL_FILE.exists():
        env = Environment(
            loader=FileSystemLoader(str(TPL_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        template = env.get_template("report.html")
        html = template.render(
            city=city,
            start=start,
            end=end,
            max_temp=f"{max_temp:.1f}" if max_temp is not None else "-",
            min_temp=f"{min_temp:.1f}" if min_temp is not None else "-",
            wettest_date=wettest_date or "-",
            wettest_rain=f"{wettest_rain:.1f}",
            pm25_avg=f"{pm25_avg:.1f}" if pm25_avg is not None else "-",
            pm25_category=pm25_cat,
            rainy_days=rainy_days,
            charts=charts_html,
            recommendation=recommendation,
            sunrise_earliest=(
                sunrise_earliest.strftime("%H:%M")
                if sunrise_earliest is not None
                else "-"
            ),
            sunset_latest=(
                sunset_latest.strftime("%H:%M") if sunset_latest is not None else "-"
            ),
            feels_like_avg=(
                f"{feels_like_avg:.1f}" if feels_like_avg is not None else "-"
            ),
            dew_point_avg=(
                f"{dew_point_avg:.1f}" if dew_point_avg is not None else "-"
            ),
            hot_days=int(df["is_hot_day"].sum()) if "is_hot_day" in df.columns else 0,
            heavy_rain_days=(
                int(df["is_heavy_rain"].sum()) if "is_heavy_rain" in df.columns else 0
            ),
            unhealthy_pm25_days=(
                int(df["is_unhealthy_pm25"].sum())
                if "is_unhealthy_pm25" in df.columns
                else 0
            ),
        )
    else:
        # Fallback template minimal
        template: Template = Template(
            """
<!doctype html><meta charset="utf-8"><title>Laporan {{ city }}</title>
<h1>Laporan Cuaca & Kualitas Udara — {{ city }}</h1>
<p>Periode: {{ start }} s/d {{ end }}</p>
<ul>
  <li>Suhu max tertinggi: {{ max_temp }} °C</li>
  <li>Hari paling basah: {{ wettest_date }} ({{ wettest_rain }} mm)</li>
  <li>Rata-rata PM2.5: {{ pm25_avg }} ({{ pm25_category }})</li>
  <li>Jumlah hari hujan: {{ rainy_days }}</li>
  <li>Rentang waktu terbit/terbenam (periode): {{ sunrise_earliest }} / {{ sunset_latest }}</li>
  <li>Rata-rata feels-like: {{ feels_like_avg }} °C</li>
  <li>Rata-rata dew point: {{ dew_point_avg }} °C</li>
    <li>Ringkasan alerts: panas={{ hot_days }}, hujan_berat={{ heavy_rain_days }}, pm25_tidak_sehat={{ unhealthy_pm25_days }}</li>
</ul>
<h2>Grafik</h2>
{% for c in charts %} {{ c | safe }} {% endfor %}
<h2>Rekomendasi</h2>
<p>{{ recommendation }}</p>
"""
        )
        html = template.render(
            city=city,
            start=start,
            end=end,
            max_temp=f"{max_temp:.1f}" if max_temp is not None else "-",
            wettest_date=wettest_date or "-",
            wettest_rain=f"{wettest_rain:.1f}",
            pm25_avg=f"{pm25_avg:.1f}" if pm25_avg is not None else "-",
            pm25_category=pm25_cat,
            rainy_days=rainy_days,
            charts=charts_html,
            recommendation=recommendation,
            sunrise_earliest=(
                sunrise_earliest.strftime("%H:%M")
                if sunrise_earliest is not None
                else "-"
            ),
            sunset_latest=(
                sunset_latest.strftime("%H:%M") if sunset_latest is not None else "-"
            ),
            feels_like_avg=(
                f"{feels_like_avg:.1f}" if feels_like_avg is not None else "-"
            ),
            dew_point_avg=(
                f"{dew_point_avg:.1f}" if dew_point_avg is not None else "-"
            ),
        )

    # Simpan file
    out_path = Path(output) if output else Path("reports") / f"{slug}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    LOG.info("Saved report -> %s", out_path)
    return str(out_path)


__all__ = ["run", "_simple_recommendation", "_pm25_category"]
