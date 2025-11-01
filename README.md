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

## Demo cepat (online)
etl-weather all --city "Bandung" --days 7 --timezone "Asia/Jakarta"
start reports\bandung.html

## Demo offline (tanpa internet)
# siapkan sample dulu
mkdir data/samples
copy tests/fixtures/weather_min.json data/samples/bandung_weather.json
copy tests/fixtures/air_min.json     data/samples/bandung_air.json
# jalankan pipeline dengan sample
etl-weather all --city "Bandung" --offline
start reports\bandung.html

## Troubleshooting
- File CSV/JSON tak ditemukan: jalankan tahap sebelumnya (fetch -> transform -> report).
- Network error: gunakan --offline atau siapkan fallback sample (default aktif).