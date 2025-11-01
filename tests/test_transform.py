import pandas as pd
from etl_weather import transform


def test_transform_produces_daily_csv(monkeypatch, tmp_data_dirs, fixtures_dir):
    # arahkan RAW_DIR & PROC_DIR ke tmp
    monkeypatch.setattr(transform, "RAW_DIR", tmp_data_dirs["raw"], raising=True)
    monkeypatch.setattr(transform, "PROC_DIR", tmp_data_dirs["processed"], raising=True)
    (transform.RAW_DIR).mkdir(parents=True, exist_ok=True)
    (transform.PROC_DIR).mkdir(parents=True, exist_ok=True)

    # tulis sample raw json
    (transform.RAW_DIR / "bandung_weather.json").write_text(
        (fixtures_dir / "weather_min.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (transform.RAW_DIR / "bandung_air.json").write_text(
        (fixtures_dir / "air_min.json").read_text(encoding="utf-8"), encoding="utf-8"
    )

    out = transform.run("Bandung")
    df = pd.read_csv(out)
    assert {
        "date",
        "temp_min",
        "temp_max",
        "total_rain",
        "pm25_avg",
        "pm10_avg",
        "pm25_category",
    } <= set(df.columns)
    assert len(df) >= 1
