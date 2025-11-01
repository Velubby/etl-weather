from etl_weather import fetch


def test_fetch_run_uses_geocode_and_saves(monkeypatch, tmp_path):
    # arahkan RAW_DIR ke tmp
    monkeypatch.setattr(fetch, "RAW_DIR", tmp_path / "data" / "raw", raising=True)
    fetch.RAW_DIR.mkdir(parents=True, exist_ok=True)

    # stub geocode_city -> koordinat Bandung
    def fake_geocode(_city: str):
        return {
            "name": "Bandung",
            "lat": -6.9175,
            "lon": 107.6191,
            "timezone": "Asia/Jakarta",
        }

    monkeypatch.setattr(fetch, "geocode_city", fake_geocode, raising=True)

    # stub _request_json -> kembalikan minimal struktur expected
    def fake_req(url, params, retries=3, timeout=10):
        if "air-quality" in url:
            return {
                "hourly": {
                    "time": ["2025-01-01T00:00"],
                    "pm2_5": [10.0],
                    "pm10": [20.0],
                }
            }
        return {
            "hourly": {
                "time": ["2025-01-01T00:00"],
                "temperature_2m": [26.0],
                "precipitation": [0.1],
            }
        }

    monkeypatch.setattr(fetch, "_request_json", fake_req, raising=True)

    res = fetch.run("Bandung", days=3, timezone="Asia/Jakarta")
    assert "weather_latest" in res and "air_latest" in res
    assert (tmp_path / "data" / "raw").exists()
