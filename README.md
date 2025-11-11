# ETL Cuaca & Kualitas Udara (Open‑Meteo)

Ambil data cuaca + kualitas udara per jam, agregasi harian, visualisasi, dan render laporan HTML. Dilengkapi dengan web UI interaktif menggunakan FastAPI dan Gemini AI untuk fun facts.

## Instalasi & Setup

```bash
# Clone dan install
git clone https://github.com/Velubby/etl-weather.git
cd etl-weather

# Install dari pyproject.toml (includes all dependencies)
pip install -e .

# Install dengan dev tools (testing, linting)
pip install -e ".[dev]"

# Setup environment (opsional untuk fitur AI)
cp .env.example .env
# Edit .env dan isi GEMINI_API_KEY dan GEMINI_MODEL
```

## Web UI (Interactive Dashboard)

Jalankan web server:
```bash
etl-weather-web
```

Kemudian buka http://localhost:8000 di browser.

### Fitur Web UI
- **Dual Search Mode**: Cari kota via text atau pilih berdasarkan provinsi/kabupaten Indonesia
- **Real-time Weather**: Data cuaca dan kualitas udara terkini dengan visualisasi interaktif
- **Fun Facts**: Fakta menarik tentang kota via Gemini AI
  - Parameter `fast=1`: Cache-first untuk respons instant, refresh di background
  - Parameter `fresh=1`: Generate variant baru (bisa lebih lambat)
  - Tombol "New variant" untuk minta fakta unik
- **AI Status**: Pill indicator menampilkan status koneksi Gemini dan model aktif
- **City Comparison**: Bandingkan hingga 5 kota sekaligus dengan chart interaktif
- **Responsive Design**: Mobile-friendly dengan header modern

### API Endpoints
- `GET /` - Dashboard utama
- `GET /search?q={city}` - Geocoding kota
- `GET /api/provinces` - List provinsi Indonesia
- `GET /api/regencies/{province_code}` - List kota/kabupaten per provinsi
- `GET /data/daily?city={city}&refresh=true` - Data harian
- `GET /data/hourly?city={city}&refresh=true` - Data per jam
- `GET /city/funfact/{city}?fast=1&fresh=0` - Fun fact kota (via Gemini)
- `GET /ai/status` - Diagnostik koneksi Gemini AI
- `GET /compare?cities=Jakarta,Surabaya&days=7` - Perbandingan multi-kota

## CLI (Command Line)

### Testing
```bash
pip install -e ".[dev]"
pytest -q
# dengan coverage:
pytest -q --cov=etl_weather --cov-report=term-missing
```

### Struktur test
- `tests/fixtures/`: Sample JSON untuk offline test
- `test_fetch.py`: Mock geocoding dan HTTP
- `test_transform.py`: Gunakan fixtures → CSV harian
- `test_report.py`: Uji rekomendasi & kategori PM2.5

### Demo cepat (online)
```bash
etl-weather all --city "Bandung" --days 7 --timezone "Asia/Jakarta"
start reports\bandung.html
```

### Demo offline (tanpa internet)
```bash
# Siapkan sample dulu
mkdir data/samples
copy tests\fixtures\weather_min.json data\samples\bandung_weather.json
copy tests\fixtures\air_min.json data\samples\bandung_air.json

# Jalankan pipeline dengan sample
etl-weather all --city "Bandung" --offline
start reports\bandung.html
```

## Konfigurasi Environment (AI Features)

Untuk mengaktifkan fun facts dengan Gemini AI, buat file `.env`:

```env
# Gemini API Key (required untuk fun facts)
GEMINI_API_KEY=your_api_key_here

# Gemini Model (opsional, bisa comma-separated untuk fallback)
# Default: gemini-2.5-flash
GEMINI_MODEL=gemini-2.5-flash
# atau multiple: gemini-2.5-flash,gemini-2.5-pro
```

Model yang diutamakan: `gemini-2.5-flash` untuk respons cepat dan varied output.

## Deployment (DirectAdmin/Passenger)

Untuk hosting di DirectAdmin dengan Passenger:

```bash
# Di server, activate virtualenv yang disediakan DirectAdmin
source /home/username/virtualenv/path/to/app/3.11/bin/activate

# Install dependencies
pip install -e .

# Buat .env file
printf "GEMINI_API_KEY=your_key\nGEMINI_MODEL=gemini-2.5-flash\n" > .env

# Passenger akan otomatis load dari passenger_wsgi.py
# Restart app di DirectAdmin panel
```

File `passenger_wsgi.py` sudah include manual ASGI→WSGI adapter, tidak perlu package tambahan.

## Teknologi Stack

- **Backend**: FastAPI, Uvicorn, Pandas, Pydantic
- **Frontend**: Vanilla JS, Vega-Lite charts, responsive CSS
- **Data Source**: Open-Meteo API (weather & air quality)
- **AI**: Google Gemini (fun facts dengan caching & variation)
- **Region Data**: wilayah.id API (Indonesian provinces/regencies)
- **Deployment**: Passenger WSGI (DirectAdmin compatible)

## Troubleshooting

- **File CSV/JSON tak ditemukan**: Jalankan tahap sebelumnya (fetch → transform → report)
- **Network error**: Gunakan `--offline` atau siapkan fallback sample
- **Fun facts tidak muncul**: Pastikan `GEMINI_API_KEY` valid dan model tersedia
- **AI status error**: Cek `/ai/status` endpoint untuk diagnostik detail
- **Search dropdown kosong**: Periksa koneksi internet untuk geocoding API