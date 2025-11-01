# ETL Cuaca & Kualitas Udara (Open‑Meteo)

Ambil data cuaca + kualitas udara per jam, agregasi harian, visualisasi, dan render laporan HTML.

## Cepat mulai
pip install -e ".[dev]"
etl-weather hello --name ETL

## Fitur (rencana)
- Fetch: Open-Meteo (weather + air quality), cache lokal
- Transform: agregasi harian (suhu min/max, total hujan, rata-rata PM)
- Viz: grafik tren (Altair)
- Report: HTML via Jinja2
- CLI: Typer

## Struktur
src/etl_weather/*; data/raw, data/processed; reports/