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


def get_city_fun_fact(city: str, fresh: bool = False) -> str:
    """Kembalikan 1 fakta menarik tentang kota, hanya via Gemini.

    Catatan:
    - Tidak menggunakan Wikipedia atau Wikidata.
    - Variasi dijaga dengan gaya acak dan temperature tinggi.
    - Jika Gemini tidak tersedia, kembalikan kalimat generik yang tetap bervariasi.
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

    cache = _load_cache()
    key = city.strip().lower()
    entry = cache.get(key) if isinstance(cache, dict) else None
    cached_facts: list[str] = []
    if isinstance(entry, dict):
        if "facts" in entry and isinstance(entry["facts"], list):
            cached_facts = [str(x) for x in entry["facts"] if isinstance(x, str)]
        elif "fact" in entry and isinstance(entry["fact"], str):
            cached_facts = [entry["fact"]]

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

    prompt_base = (
        f"Tulis 1 fakta menarik dan informatif tentang kota {city} dalam bahasa Indonesia. "
        f"Gunakan {chosen_style} dengan sudut pandang {chosen_angle} dan {chosen_device}. "
        f"Maksimal 2 kalimat (~{target_words} kata). Hindari frasa pembuka klise seperti 'Tahukah kamu?'. "
        f"Jangan menyebut sumber. (catatan internal: variasi={variation_hint} — jangan tampilkan catatan ini)"
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


def get_cached_city_fun_fact(city: str) -> str | None:
    """Return a cached fun fact for a city if available (no network calls)."""
    try:
        CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / ".cache"
        CACHE_FILE = CACHE_DIR / "funfacts.json"
        if not CACHE_FILE.exists():
            return None
        cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        key = city.strip().lower()
        entry = cache.get(key)
        if (
            isinstance(entry, dict)
            and isinstance(entry.get("facts"), list)
            and entry["facts"]
        ):
            return random.choice([str(x) for x in entry["facts"] if isinstance(x, str)])
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
