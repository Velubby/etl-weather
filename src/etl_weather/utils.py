from __future__ import annotations
import httpx


def geocode_city(city: str) -> dict:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    with httpx.Client(timeout=10) as c:
        r = c.get(
            url, params={"name": city, "count": 1, "language": "id", "format": "json"}
        )
        r.raise_for_status()
        j = r.json()
    if not j.get("results"):
        raise ValueError(f"Kota '{city}' tidak ditemukan")
    res = j["results"][0]
    return {
        "name": res["name"],
        "lat": res["latitude"],
        "lon": res["longitude"],
        "timezone": res.get("timezone", "auto"),
    }
