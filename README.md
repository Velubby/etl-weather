# ETL Cuaca & Kualitas Udara (Open‑Meteo)

Ambil data cuaca + kualitas udara per jam, agregasi harian, visualisasi, dan render laporan HTML.

## Testing
pip install -e ".[dev]"
pytest -q
# dengan coverage:
pytest -q --cov=etl_weather --cov-report=term-missing
## Struktur test
- tests/fixtures/ : sample JSON untuk offline test (tanpa internet)
- test_fetch.py    : mock geocoding dan HTTP; verifikasi file raw tersimpan
- test_transform.py: gunakan fixtures -> hasilkan CSV harian
- test_report.py   : uji aturan rekomendasi & kategori PM2.5