# ETL Weather & Air Quality Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A comprehensive ETL (Extract, Transform, Load) platform for weather and air quality data, featuring an interactive web dashboard with AI-powered insights. Built with FastAPI, powered by Open-Meteo API, and enhanced with Google Gemini AI for contextual city facts.

---

## Features

- **🌐 Interactive Web Dashboard**: Real-time weather visualization with responsive design
- **🤖 AI-Powered Insights**: Location-aware city facts using Google Gemini AI
- **📊 Data Visualization**: Interactive charts with Vega-Lite
- **🔍 Smart Search**: Dual-mode city search (text or hierarchical province/regency)
- **📈 Multi-City Comparison**: Compare weather data across multiple cities
- **🚀 Production-Ready**: Deployable via Passenger WSGI (DirectAdmin compatible)
- **✅ Fully Tested**: Comprehensive test suite with pytest

---

## Quick Start

```bash
# Clone repository
git clone https://github.com/Velubby/etl-weather.git
cd etl-weather

# Install dependencies
pip install -e .

# (Optional) Enable AI features
cp .env.example .env
# Edit .env: add GEMINI_API_KEY and GEMINI_MODEL

# Launch web interface
etl-weather-web
# Navigate to http://localhost:8000
```

---

## Installation

### Standard Installation

```bash
pip install -e .
```

### Development Installation

Includes testing and linting tools:

```bash
pip install -e ".[dev]"
```

### Environment Configuration

For AI-powered features, create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

**Supported Models**:
- `gemini-2.5-flash` (recommended for fast, varied responses)
- `gemini-2.5-pro`
- Comma-separated list for fallback: `gemini-2.5-flash,gemini-2.5-pro`

---

## Web Dashboard

### Starting the Server

```bash
etl-weather-web
```

Access the dashboard at `http://localhost:8000`

### Dashboard Features

#### 🔍 Smart City Search
- **Text Search**: Type any city name globally
- **Hierarchical Browse**: Navigate Indonesian provinces and regencies
- Real-time autocomplete with location disambiguation (province, country)

#### 🌤️ Weather Data Visualization
- **Today View**: Current conditions with hourly breakdown
- **7-Day Forecast**: Temperature trends, precipitation, and air quality
- **Hourly Details**: Interactive charts with temperature, humidity, wind, and rain data

#### 🤖 AI-Powered City Facts
Location-aware insights powered by Google Gemini:
- **Fast Mode** (`fast=1`): Instant cache-first response with background refresh
- **Fresh Mode** (`fresh=1`): Generate new variant (may take longer)
- **Smart Disambiguation**: Different facts for cities with identical names in different regions
- One-click refresh for new variations

#### 📊 Multi-City Comparison
Compare weather metrics across up to 5 cities simultaneously with synchronized visualizations.

#### 📱 Responsive Design
Optimized for desktop and mobile with modern, accessible UI.

### API Documentation

Interactive API documentation available at `/docs` when server is running.

**Key Endpoints**:
- `GET /search` - City geocoding with autocomplete
- `GET /api/provinces` - Indonesian provinces
- `GET /api/regencies/{province_id}` - Regencies by province
- `GET /data/daily` - Daily weather aggregates
- `GET /data/hourly` - Hourly weather data
- `GET /city/funfact/{city}` - AI-generated city facts
- `GET /compare` - Multi-city comparison data

---

## Command-Line Interface

### Available Commands

```bash
# Full ETL pipeline (fetch → transform → report)
etl-weather all --city "Bandung" --days 7 --timezone "Asia/Jakarta"

# Individual pipeline stages
etl-weather fetch --city "Jakarta" --days 5
etl-weather transform --city "Jakarta"
etl-weather report --city "Jakarta"

# Offline mode (uses sample data)
etl-weather all --city "Bandung" --offline
```

### Testing

```bash
# Run test suite
pytest -q

# With coverage report
pytest --cov=etl_weather --cov-report=term-missing

# Lint code
ruff check
```

**Test Structure**:
- `tests/fixtures/` - Sample JSON for offline testing
- `test_fetch.py` - Geocoding and HTTP request mocking
- `test_transform.py` - CSV transformation validation
- `test_report.py` - Air quality categorization and recommendations

### Quick Demo (Online)

```bash
etl-weather all --city "Bandung" --days 7 --timezone "Asia/Jakarta"
# Open generated report
start reports/bandung.html  # Windows
open reports/bandung.html   # macOS
xdg-open reports/bandung.html  # Linux
```

### Offline Demo

```bash
# Prepare sample data
mkdir -p data/samples
cp tests/fixtures/weather_min.json data/samples/bandung_weather.json
cp tests/fixtures/air_min.json data/samples/bandung_air.json

# Run pipeline with sample data
etl-weather all --city "Bandung" --offline
start reports/bandung.html
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Required for AI features
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Model selection (default: gemini-2.5-flash)
GEMINI_MODEL=gemini-2.5-flash

# Multiple models for fallback
# GEMINI_MODEL=gemini-2.5-flash,gemini-2.5-pro
```

### Model Selection

- **gemini-2.5-flash**: Recommended for fast, diverse responses
- **gemini-2.5-pro**: Higher quality, slower generation
- **Comma-separated list**: Automatic fallback if primary model unavailable

### Security Notes

- Never commit `.env` to version control
- Use `.env.example` as a template
- Store production keys in secure environment variable managers

---

## Production Deployment

### DirectAdmin with Passenger WSGI

This project includes a pre-configured `passenger_wsgi.py` with a manual ASGI→WSGI adapter (no external dependencies required).

#### Deployment Steps

1. **Activate DirectAdmin Virtual Environment**
   ```bash
   source /home/username/virtualenv/path/to/app/3.11/bin/activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -e .
   ```

3. **Configure Environment**
   ```bash
   cat > .env << EOF
   GEMINI_API_KEY=your_production_key
   GEMINI_MODEL=gemini-2.5-flash
   EOF
   ```

4. **Restart Application**
   - Via DirectAdmin panel: Navigate to Python App settings → Restart
   - Via command line: `touch tmp/restart.txt` (in app root)

#### Application Structure

```
your-app-root/
├── passenger_wsgi.py    # WSGI entry point
├── .env                 # Environment variables (excluded from git)
├── src/etl_weather/     # Application code
└── tmp/
    └── restart.txt      # Touch to restart
```

#### Troubleshooting Deployment

- **500 Errors**: Check Passenger error logs in DirectAdmin
- **Module Import Failures**: Ensure `src/` is in Python path (handled by `passenger_wsgi.py`)
- **Environment Variables Not Loading**: Verify `.env` file location and permissions

---

## Technology Stack

### Backend
- **Framework**: FastAPI (async, modern Python web framework)
- **Server**: Uvicorn (ASGI server)
- **Data Processing**: Pandas, Pydantic v2
- **HTTP Client**: httpx (async-capable)
- **Environment**: python-dotenv

### Frontend
- **UI Framework**: Vanilla JavaScript (no heavy frameworks)
- **Visualization**: Vega-Lite (declarative grammar of graphics)
- **Styling**: Responsive CSS with modern flexbox/grid layouts
- **Icons**: SVG-based custom icon system

### Data Sources
- **Weather & Air Quality**: [Open-Meteo API](https://open-meteo.com/)
- **Geocoding**: Open-Meteo Geocoding API
- **Regional Data**: [wilayah.id API](https://wilayah.id/) (Indonesian administrative divisions)

### AI Integration
- **Provider**: Google Gemini AI
- **Models**: gemini-2.5-flash, gemini-2.5-pro
- **Features**: Location-aware fact generation, response caching, prompt variation

### Deployment
- **WSGI Adapter**: Custom manual ASGI→WSGI bridge (no external deps)
- **Hosting**: Passenger WSGI compatible (DirectAdmin, shared hosting)
- **Production Server**: Suitable for Gunicorn, Uvicorn, or Passenger

---

## Troubleshooting

### Common Issues

#### Data Files Not Found
**Problem**: `FileNotFoundError` for CSV/JSON files

**Solution**: Ensure pipeline stages run in order:
```bash
etl-weather fetch --city "YourCity"
etl-weather transform --city "YourCity"
etl-weather report --city "YourCity"
```

#### Network Errors
**Problem**: API requests failing or timing out

**Solutions**:
- Use offline mode: `--offline` flag
- Prepare sample data in `data/samples/`
- Check firewall/proxy settings
- Verify Open-Meteo API availability

#### AI Features Not Working
**Problem**: Fun facts not generating or showing errors

**Solutions**:
1. Verify `GEMINI_API_KEY` in `.env` file
2. Check model name spelling: `GEMINI_MODEL=gemini-2.5-flash`
3. Ensure `.env` is in project root
4. Check Passenger error logs (production)
5. Verify API key has Gemini API access enabled

**Never commit `.env` to version control**

#### Search Dropdown Empty
**Problem**: City search returns no results

**Solutions**:
- Check internet connectivity
- Verify Open-Meteo Geocoding API is accessible
- Try different search terms or broader queries
- Check browser console for JavaScript errors

#### Location Disambiguation Issues
**Problem**: Cities with identical names showing same facts

**Explanation**: The system now uses geocoding (coordinates, province, country) to generate location-specific prompts and cache keys. Each unique location gets distinct facts.

**To clear old cache**:
```bash
rm data/.cache/funfacts.json
```

#### Production Deployment Issues

**Problem**: 500 errors on DirectAdmin/Passenger

**Solutions**:
1. Check Passenger error logs in DirectAdmin panel
2. Verify Python version compatibility (3.11+)
3. Ensure all dependencies installed in virtualenv
4. Confirm `passenger_wsgi.py` is in app root
5. Check file permissions on `.env` and app directories

**Problem**: Environment variables not loading

**Solutions**:
- Verify `.env` file exists in app root
- Check file permissions: `chmod 600 .env`
- Confirm no syntax errors in `.env`
- Restart Passenger: `touch tmp/restart.txt`

---

## Project Structure

```
etl-weather/
├── src/etl_weather/
│   ├── fetch.py           # Data fetching from APIs
│   ├── transform.py       # Data transformation & aggregation
│   ├── report.py          # HTML report generation
│   ├── web.py             # FastAPI application & routes
│   ├── utils.py           # AI integration, geocoding, helpers
│   └── webui/             # Frontend assets
│       ├── templates/     # Jinja2 HTML templates
│       └── static/        # CSS, JS, icons
├── tests/                 # Test suite
│   ├── fixtures/          # Sample data for testing
│   └── test_*.py          # Unit tests
├── data/
│   ├── raw/               # Fetched JSON data
│   ├── processed/         # Transformed CSV data
│   ├── samples/           # Offline mode samples
│   └── .cache/            # AI response cache
├── reports/               # Generated HTML reports
├── passenger_wsgi.py      # WSGI entry point
├── pyproject.toml         # Project metadata & dependencies
└── .env                   # Environment variables (not in git)
```

---

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Run tests**: `pytest -q`
4. **Run linter**: `ruff check`
5. **Commit changes**: Follow conventional commits
6. **Submit pull request**

### Code Style

- **Formatting**: Black (automated via pre-commit)
- **Linting**: Ruff
- **Type Hints**: Encouraged for new code
- **Docstrings**: Required for public functions

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **Weather Data**: [Open-Meteo](https://open-meteo.com/) for free weather and air quality API
- **Regional Data**: [wilayah.id](https://wilayah.id/) for Indonesian administrative divisions
- **AI**: Google Gemini for generative AI capabilities
- **Visualization**: [Vega-Lite](https://vega.github.io/vega-lite/) for declarative graphics

---

## Support

- **Issues**: [GitHub Issues](https://github.com/Velubby/etl-weather/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Velubby/etl-weather/discussions)
- **Documentation**: [API Docs](http://localhost:8000/docs) (when server running)

---

**Made with ❤️ using FastAPI and Gemini AI**