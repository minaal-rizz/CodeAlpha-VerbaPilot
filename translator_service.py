#translation_service.py
# translator_service.py
import os
import json
import requests
from pathlib import Path
from functools import lru_cache
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.translation.text import TextTranslationClient
from azure.ai.translation.text.models import InputTextItem

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent

# ---------- helpers ----------
def _safe_load_json(path: Path):
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def _get_var(name: str) -> str | None:
    """
    Order:
      1) OS/.env
      2) Streamlit secrets (only if they exist)
    Never crashes if secrets.toml is missing.
    """
    val = os.getenv(name)
    if val:
        return val
    try:
        import streamlit as st
        # wrap access in try to avoid StreamlitSecretNotFoundError
        try:
            return st.secrets[name]
        except Exception:
            return None
    except Exception:
        return None

# ---------- Azure client ----------
@lru_cache(maxsize=1)
def _get_client():
    key      = _get_var("AZURE_TRANSLATOR_KEY")
    endpoint = _get_var("AZURE_TRANSLATOR_ENDPOINT")
    region   = _get_var("AZURE_TRANSLATOR_REGION")
    if not all([key, endpoint, region]):
        raise RuntimeError("Missing Azure Translator env vars.")
    return TextTranslationClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key),
        region=region
    )

# ---------- Translation ----------
def translate(text: str, to_lang: str, from_lang: str | None = None) -> dict:
    client = _get_client()
    body = [InputTextItem(text=text)]
    kwargs = {"to_language": [to_lang]}
    if from_lang and from_lang.lower() != "auto":
        kwargs["from_language"] = from_lang
    result = client.translate(body=body, **kwargs)
    item = result[0]
    translated = item.translations[0].text
    detected = getattr(item, "detected_language", None)
    return {"translated": translated, "detected": detected.language if detected else None}

def multi_translate(text: str, targets: list[str], from_lang: str | None = None) -> dict:
    client = _get_client()
    body = [InputTextItem(text=text)]
    kwargs = {"to_language": targets}
    if from_lang and from_lang.lower() != "auto":
        kwargs["from_language"] = from_lang
    results = client.translate(body=body, **kwargs)[0].translations
    return {t.to: t.text for t in results}

# ---------- Languages ----------
LANG_URL = "https://api.cognitive.microsofttranslator.com/languages?api-version=3.0&scope=translation"

@lru_cache(maxsize=1)
def supported_languages() -> list[dict]:
    data = requests.get(LANG_URL, timeout=10).json()
    trans = data["translation"]
    return sorted(
        [{"code": code, "name": info["name"]} for code, info in trans.items()],
        key=lambda d: d["name"]
    )

# ---------- Idioms & Slang ----------
@lru_cache(maxsize=1)
def _load_phrase_db() -> dict:
    def normalize(raw):
        out = {}
        if isinstance(raw, dict):
            for k, v in raw.items():
                out[k.lower()] = v
        elif isinstance(raw, list):
            for item in raw:
                phrase = str(item.get("phrase", "")).strip()
                meaning = str(item.get("meaning", "")).strip()
                if phrase:
                    out[phrase.lower()] = meaning
        return out

    idioms_raw = _safe_load_json(BASE_DIR / "idioms.json")
    slangs_raw = _safe_load_json(BASE_DIR / "slang.json")
    return {"idioms": normalize(idioms_raw), "slangs": normalize(slangs_raw)}

def explain_idioms_slang(text: str) -> list[dict]:
    text_low = text.lower()
    db = _load_phrase_db()
    found = []
    for phrase, meaning in db["idioms"].items():
        if phrase in text_low:
            found.append({"phrase": phrase, "meaning": meaning, "type": "idiom"})
    for phrase, meaning in db["slangs"].items():
        if phrase in text_low:
            found.append({"phrase": phrase, "meaning": meaning, "type": "slang"})
    return found

# ---------- Daily challenge ----------
DEFAULT_POOL = [
    "How are you?", "I’m fine, thank you.", "What’s your name?",
    "Nice to meet you.", "Where are you from?", "See you later."
]

@lru_cache(maxsize=1)
def challenge_pool() -> list[str]:
    data = _safe_load_json(BASE_DIR / "phrases_en.json")
    pool: list[str] = []
    if isinstance(data, list):
        pool = [str(x).strip() for x in data if str(x).strip()]
    elif isinstance(data, dict):
        pool = [str(v).strip() for v in data.values() if str(v).strip()]
    return pool if pool else DEFAULT_POOL
