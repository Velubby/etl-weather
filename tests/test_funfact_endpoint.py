import json
from fastapi.testclient import TestClient
from etl_weather import web

client = TestClient(web.app)


def test_city_funfact_returns_payload_for_existing_city():
    # Use a city that has processed data in repository (e.g., jakarta)
    r = client.get('/city-funfact?city=jakarta')
    assert r.status_code == 200
    data = r.json()
    # Expect we have a city_funfact string
    assert 'city_funfact' in data
    assert isinstance(data.get('city_funfact'), str)