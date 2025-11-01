from etl_weather.report import _simple_recommendation, _pm25_category


def test_pm25_category_thresholds():
    assert _pm25_category(10) == "Baik"
    assert _pm25_category(20) == "Sedang"
    assert _pm25_category(50) == "Tidak sehat (sensitif)"
    assert _pm25_category(100) == "Tidak sehat"


def test_recommendation_rules():
    msg = _simple_recommendation(max_temp=35, pm25_avg=60, rainy_days=4)
    assert "masker" in msg.lower() or "mask" in msg.lower()
    assert "panas" in msg.lower()
    assert "hujan" in msg.lower()
