from __future__ import annotations
import httpx
import re
import unicodedata
import os
import json
import time
from pathlib import Path
import random

# Optional Google Gemini SDK. Don't hard-require it at import time.
try:
    import google.generativeai as genai  # type: ignore
except Exception:  # SDK not installed or unavailable
    genai = None  # fallback paths will be used


def _extract_text_from_genai_response(resp: object) -> str | None:
    """Try several common response shapes from google.generativeai and return text if found."""
    if resp is None:
        return None
    # dict-like responses
    try:
        # candidates -> text/content
        if isinstance(resp, dict):
            # common: {'candidates': [{'content': '...'}]}
            if "candidates" in resp and resp["candidates"]:
                c0 = resp["candidates"][0]
                for k in ("content", "text", "output", "message"):
                    if isinstance(c0, dict) and k in c0 and c0[k]:
                        return str(c0[k])
            # common: {'output': '...'} or {'text': '...'}
            for k in ("output", "text", "content", "result"):
                if k in resp and resp[k]:
                    return str(resp[k])
        # object with attributes (some SDKs return objects)
        for attr in ("text", "content", "output", "result", "message"):
            if hasattr(resp, attr):
                val = getattr(resp, attr)
                if isinstance(val, str) and val:
                    return val
        # nested common attribute
        if hasattr(resp, "candidates") and resp.candidates:
            c0 = resp.candidates[0]
            if hasattr(c0, "content"):
                return c0.content
    except Exception:
        return None
    return None


def get_city_fun_fact(
    city: str,
    fresh: bool = False,
    lat: float | None = None,
    lon: float | None = None,
    admin1: str | None = None,
    country: str | None = None,
) -> str:
    """Kembalikan 1 fakta menarik tentang kota secara kontekstual (lokasi spesifik).

    Peningkatan:
    - Geocoding dipakai untuk mendapatkan koordinat (lat/lon), negara, dan admin1 (provinsi) agar nama kota yang sama bisa dibedakan.
    - Prompt diperkaya dengan lat/lon & region supaya model tidak memberi fakta generik untuk kota yang ambigu.
    - Tidak menggunakan Wikipedia atau Wikidata langsung.
    - Variasi dijaga dengan gaya acak dan temperature tinggi.
    - Jika Gemini tidak tersedia, kembalikan pesan yang menjelaskan kebutuhan konfigurasi.
    """

    api_key = os.getenv("GEMINI_API_KEY")

    # persistent cache directory (data/.cache/funfacts.json)
    CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / ".cache"
    CACHE_FILE = CACHE_DIR / "funfacts.json"

    def _load_cache() -> dict:
        try:
            if CACHE_FILE.exists():
                return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return {}

    def _save_cache(d: dict) -> None:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(
                json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    # cache will be initialized after we know the final lookup key (location-aware)
    cache = _load_cache()
    cached_facts: list[str] = []

    # Randomize style and angle to encourage diverse responses every call
    styles = [
        "gaya santai",
        "gaya ramah wisata",
        "nuansa sejarah",
        "fokus kuliner",
        "sudut arsitektur/ruang kota",
        "nuansa budaya-pop",
        "sentuhan humor ringan",
    ]
    angles = [
        "sejarah lokal",
        "kuliner khas",
        "arsitektur atau ruang publik",
        "musik/seni dan festival",
        "olahraga atau komunitas",
        "ekonomi lokal atau kerajinan",
        "transportasi atau mobilitas harian",
        "tradisi dan bahasa",
    ]
    devices = [
        "metafora ringan",
        "perbandingan kontekstual",
        "satu angka atau tahun penting",
        "nama julukan yang khas",
        "referensi landmark",
        "aktivitas warga di waktu tertentu",
    ]
    chosen_style = random.choice(styles)
    chosen_angle = random.choice(angles)
    chosen_device = random.choice(devices)
    target_words = random.randint(18, 32)
    variation_hint = f"v{random.randint(1000,9999)}-{random.choice('ABCDE')}"

    # Ambil konteks geolokasi untuk disambiguasi
    geo_context = None
    # Prefer explicit parameters if provided
    if lat is not None and lon is not None:
        geo_context = {
            "name": city,
            "country": country,
            "admin1": admin1,
            "lat": lat,
            "lon": lon,
            "timezone": None,
        }
    else:
        try:
            # Reuse lightweight public geocoding (Open-Meteo) for single result
            import httpx

            with httpx.Client(timeout=6.0) as gc:
                gr = gc.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={
                        "name": city,
                        "count": 1,
                        "language": "id",
                        "format": "json",
                    },
                )
                if gr.status_code == 200:
                    gj = gr.json()
                    if gj.get("results"):
                        r0 = gj["results"][0]
                        geo_context = {
                            "name": r0.get("name") or city,
                            "country": r0.get("country"),
                            "admin1": r0.get("admin1"),
                            "lat": r0.get("latitude"),
                            "lon": r0.get("longitude"),
                            "timezone": r0.get("timezone"),
                        }
        except Exception:
            geo_context = None

    location_clause = ""
    if geo_context:
        # Build a compact disambiguation string
        loc_parts = []
        if geo_context.get("admin1"):
            loc_parts.append(str(geo_context["admin1"]))
        if geo_context.get("country"):
            loc_parts.append(str(geo_context["country"]))
        coords = None
        if geo_context.get("lat") is not None and geo_context.get("lon") is not None:
            coords = f"({geo_context['lat']:.2f}, {geo_context['lon']:.2f})"
        loc_str = ", ".join(loc_parts) if loc_parts else "lokasi tidak pasti"
        location_clause = (
            f"Kota ini merujuk pada '{geo_context.get('name', city)}' di {loc_str} {coords or ''}. "
            "Jika ada kota lain bernama sama, fokuskan fakta pada lokasi ini. "
        )

    # Decide cache key (location-aware if possible, legacy fallback otherwise)
    if (
        geo_context
        and geo_context.get("lat") is not None
        and geo_context.get("lon") is not None
    ):
        lat = float(geo_context.get("lat"))
        lon = float(geo_context.get("lon"))
        name_norm = str(geo_context.get("name", city)).strip().lower()
        admin1_norm = str(geo_context.get("admin1") or "").strip().lower()
        country_norm = str(geo_context.get("country") or "").strip().lower()
        key = f"{name_norm}|{admin1_norm}|{country_norm}|{lat:.3f},{lon:.3f}"
    else:
        key = city.strip().lower()

    # Load cached facts for the chosen key (and support legacy key migration)
    entry = cache.get(key) if isinstance(cache, dict) else None
    if isinstance(entry, dict):
        if "facts" in entry and isinstance(entry["facts"], list):
            cached_facts = [str(x) for x in entry["facts"] if isinstance(x, str)]
        elif "fact" in entry and isinstance(entry["fact"], str):
            cached_facts = [entry["fact"]]
    # Legacy lookup: if location-aware key not found and we used it, also try plain city
    if not cached_facts and key != city.strip().lower():
        legacy_entry = (
            cache.get(city.strip().lower()) if isinstance(cache, dict) else None
        )
        if isinstance(legacy_entry, dict):
            if "facts" in legacy_entry and isinstance(legacy_entry["facts"], list):
                cached_facts = [
                    str(x) for x in legacy_entry["facts"] if isinstance(x, str)
                ]
            elif "fact" in legacy_entry and isinstance(legacy_entry["fact"], str):
                cached_facts = [legacy_entry["fact"]]

    prompt_base = (
        f"{location_clause}Tulis 1 fakta menarik dan informatif tentang kota {city} dalam bahasa Indonesia. "
        f"Gunakan {chosen_style} dengan sudut pandang {chosen_angle} dan {chosen_device}. "
        f"Maksimal 2 kalimat (~{target_words} kata). Hindari frasa pembuka klise seperti 'Tahukah kamu?'. "
        f"Hindari menyebut sumber atau berspekulasi tanpa dasar lokal. (catatan internal: variasi={variation_hint} — jangan tampilkan catatan ini)"
    )

    # Use Gemini to generate the sentence
    if api_key and genai is not None:
        try:
            genai.configure(api_key=api_key)
            enriched_prompt = prompt_base

            # Prefer GenerativeModel (newer SDK) with robust model fallback names
            if hasattr(genai, "GenerativeModel"):
                # Accept comma-separated env and normalize with/without 'models/' prefix
                env_models = os.getenv("GEMINI_MODEL") or ""
                env_list = [s.strip() for s in env_models.split(",") if s.strip()]
                priority = [
                    "gemini-2.5-flash",
                    "gemini-2.5-flash-preview-05-20",
                    "gemini-2.5-flash-preview-09-2025",
                    "gemini-2.5-flash-lite",
                    "gemini-2.5-pro",
                ]
                base = env_list + priority
                # expand names to include both 'models/<name>' and '<name>'
                expanded: list[str] = []
                for name in base:
                    if not name:
                        continue
                    if name.startswith("models/"):
                        expanded.append(name)
                        expanded.append(name.replace("models/", "", 1))
                    else:
                        expanded.append(name)
                        expanded.append("models/" + name)
                # de-duplicate preserving order
                seen = set()
                model_candidates = [
                    x for x in expanded if not (x in seen or seen.add(x))
                ]
                for model_name in model_candidates:
                    try:
                        model = genai.GenerativeModel(model_name=model_name)
                        resp = model.generate_content(
                            enriched_prompt,
                            generation_config={
                                "temperature": 1.15,
                                "top_p": 0.95,
                                "top_k": 40,
                                "max_output_tokens": 80,
                            },
                        )
                        txt = _extract_text_from_genai_response(resp)
                        if txt and txt.strip():
                            val = txt.strip()
                            if val not in cached_facts:
                                cached_facts.append(val)
                                cached_facts = cached_facts[-7:]
                            cache[key] = {"facts": cached_facts, "ts": time.time()}
                            _save_cache(cache)
                            return val
                    except Exception:
                        continue

            # Fallback older APIs
            try:
                if hasattr(genai, "generate_text"):
                    env_models = os.getenv("GEMINI_MODEL") or ""
                    env_list = [s.strip() for s in env_models.split(",") if s.strip()]
                    priority = [
                        "gemini-2.5-flash",
                        "gemini-2.5-flash-preview-05-20",
                        "gemini-2.5-flash-preview-09-2025",
                        "gemini-2.5-flash-lite",
                        "gemini-2.5-pro",
                    ]
                    base = env_list + priority
                    expanded: list[str] = []
                    for name in base:
                        if not name:
                            continue
                        if name.startswith("models/"):
                            expanded.append(name)
                            expanded.append(name.replace("models/", "", 1))
                        else:
                            expanded.append(name)
                            expanded.append("models/" + name)
                    seen = set()
                    model_list = [x for x in expanded if not (x in seen or seen.add(x))]
                    for model_name in model_list:
                        try:
                            resp = genai.generate_text(
                                model=model_name,
                                prompt=enriched_prompt,
                                temperature=1.15,
                                max_output_tokens=80,
                                top_p=0.95,
                                top_k=40,
                            )
                            txt = _extract_text_from_genai_response(resp)
                            if txt and txt.strip():
                                val = txt.strip()
                                if val not in cached_facts:
                                    cached_facts.append(val)
                                    cached_facts = cached_facts[-7:]
                                cache[key] = {"facts": cached_facts, "ts": time.time()}
                                _save_cache(cache)
                                return val
                        except Exception:
                            continue
            except Exception:
                pass

            try:
                if hasattr(genai, "generate"):
                    env_models = os.getenv("GEMINI_MODEL") or ""
                    env_list = [s.strip() for s in env_models.split(",") if s.strip()]
                    priority = [
                        "gemini-2.5-flash",
                        "gemini-2.5-flash-preview-05-20",
                        "gemini-2.5-flash-preview-09-2025",
                        "gemini-2.5-flash-lite",
                        "gemini-2.5-pro",
                    ]
                    base = env_list + priority
                    expanded: list[str] = []
                    for name in base:
                        if not name:
                            continue
                        if name.startswith("models/"):
                            expanded.append(name)
                            expanded.append(name.replace("models/", "", 1))
                        else:
                            expanded.append(name)
                            expanded.append("models/" + name)
                    seen = set()
                    model_list = [x for x in expanded if not (x in seen or seen.add(x))]
                    for model_name in model_list:
                        try:
                            resp = genai.generate(
                                model=model_name,
                                input=enriched_prompt,
                                temperature=1.15,
                                max_output_tokens=80,
                                top_p=0.95,
                                top_k=40,
                            )
                            txt = _extract_text_from_genai_response(resp)
                            if txt and txt.strip():
                                val = txt.strip()
                                if val not in cached_facts:
                                    cached_facts.append(val)
                                    cached_facts = cached_facts[-7:]
                                cache[key] = {"facts": cached_facts, "ts": time.time()}
                                _save_cache(cache)
                                return val
                        except Exception:
                            continue
            except Exception:
                pass

        except Exception:
            # Ignore SDK errors and fall through to cache/default
            pass

    # If Gemini not available or failed, return a clear message (no generic fallback)
    return (
        "Maaf, fun fact hanya tersedia melalui Gemini. Pastikan GEMINI_API_KEY dan GEMINI_MODEL terset "
        "serta model memiliki akses."
    )

    # Last resort: return a cached variant if available
    if cached_facts:
        return random.choice(cached_facts)

    return "Maaf, belum bisa menampilkan fakta saat ini. Coba lagi nanti."


def get_cached_city_fun_fact(
    city: str,
    lat: float | None = None,
    lon: float | None = None,
    admin1: str | None = None,
    country: str | None = None,
) -> str | None:
    """Return a cached fun fact for a city if available (no network calls).

    Uses location-aware key if previously stored, but falls back to legacy city-only key.
    """
    try:
        CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / ".cache"
        CACHE_FILE = CACHE_DIR / "funfacts.json"
        if not CACHE_FILE.exists():
            return None
        cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))

        # Compose candidates using explicit parameters first (no network call)
        key_candidates: list[str] = []
        if lat is not None and lon is not None:
            name_norm = city.strip().lower()
            admin1_norm = (admin1 or "").strip().lower()
            country_norm = (country or "").strip().lower()
            key_candidates.append(
                f"{name_norm}|{admin1_norm}|{country_norm}|{float(lat):.3f},{float(lon):.3f}"
            )

        # Always include legacy city-only key as a fallback
        key_candidates.append(city.strip().lower())

        for k in key_candidates:
            entry = cache.get(k)
            if (
                isinstance(entry, dict)
                and isinstance(entry.get("facts"), list)
                and entry["facts"]
            ):
                return random.choice(
                    [str(x) for x in entry["facts"] if isinstance(x, str)]
                )
            if isinstance(entry, dict) and isinstance(entry.get("fact"), str):
                return str(entry["fact"])  # very old format
    except Exception:
        return None
    return None


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
