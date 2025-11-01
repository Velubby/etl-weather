from __future__ import annotations
import httpx
import re
import unicodedata


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


def slugify(text: str) -> str:
    # Normalisasi dan hilangkan aksen, ganti non-alfanumerik dengan '-'
    text_norm = unicodedata.normalize("NFKD", text)
    text_no_accents = "".join(c for c in text_norm if not unicodedata.combining(c))
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text_no_accents).strip("-").lower()
    return slug or "city"
