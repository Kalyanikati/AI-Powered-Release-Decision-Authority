import os
import re
import unicodedata
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from langdetect import detect_langs

SPEAKER_RE = re.compile(r"^\s*([^:]{1,40})\s*:\s*(.+)$")
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
LATIN_RE = re.compile(r"[A-Za-z]")

_FASTTEXT_MODEL = None  # type: Any


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _models_dir() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")


def _ensure_fasttext_model() -> Optional[str]:
    models_dir = _models_dir()
    os.makedirs(models_dir, exist_ok=True)

    ftz_path = os.path.join(models_dir, "lid.176.ftz")
    bin_path = os.path.join(models_dir, "lid.176.bin")

    # Prefer already available local files
    if os.path.exists(ftz_path):
        return ftz_path
    if os.path.exists(bin_path):
        return bin_path

    # Download small model first (faster, git-safe if kept untracked)
    url = os.getenv(
        "FASTTEXT_MODEL_URL",
        "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz",
    )

    try:
        print("fastText model not found. Downloading lid.176.ftz (first-time setup)...")
        urllib.request.urlretrieve(url, ftz_path)
        print("fastText model downloaded:", ftz_path)
        return ftz_path
    except Exception as exc:
        print("fastText model download failed. Using fallback language detection.", exc)
        return None


def _load_fasttext_model():
    global _FASTTEXT_MODEL
    if _FASTTEXT_MODEL is not None:
        return _FASTTEXT_MODEL

    model_path = _ensure_fasttext_model()
    if not model_path:
        _FASTTEXT_MODEL = False
        return _FASTTEXT_MODEL

    try:
        import fasttext

        _FASTTEXT_MODEL = fasttext.load_model(model_path)
    except Exception as exc:
        print("fastText model load failed. Falling back to langdetect.", exc)
        _FASTTEXT_MODEL = False

    return _FASTTEXT_MODEL


def _script_ratio(text: str) -> Tuple[float, float]:
    if not text:
        return 0.0, 0.0
    total = float(max(len(text), 1))
    dev = len(DEVANAGARI_RE.findall(text)) / total
    lat = len(LATIN_RE.findall(text)) / total
    return dev, lat


def detect_language_hint(text: str) -> Tuple[str, float]:
    text = text.strip()
    if not text:
        return "unknown", 0.0

    dev_ratio, lat_ratio = _script_ratio(text)

    # script-first code-mix hint
    if dev_ratio > 0.12 and lat_ratio > 0.12:
        return "code-mix", 0.75

    # fastText if available
    ft_model = _load_fasttext_model()
    if ft_model and ft_model is not False:
        try:
            labels, probs = ft_model.predict(text.replace("\n", " "), k=2)
            top = labels[0].replace("__label__", "")
            conf = float(probs[0])
            top2 = labels[1].replace("__label__", "") if len(labels) > 1 else ""
            conf2 = float(probs[1]) if len(probs) > 1 else 0.0

            if {"en", "hi"} == {top, top2} and (conf > 0.25 and conf2 > 0.20):
                return "code-mix", max(conf, conf2)

            if top in {"en", "hi"}:
                # If script strongly suggests mix, override to code-mix
                if top == "hi" and lat_ratio > 0.15:
                    return "code-mix", conf
                if top == "en" and dev_ratio > 0.10:
                    return "code-mix", conf
                return top, conf
        except Exception:
            pass

    # fallback: langdetect
    try:
        probs = detect_langs(text)
        if probs:
            top = probs[0]
            lang = top.lang
            conf = float(top.prob)

            if lang == "hi":
                if lat_ratio > 0.15:
                    return "code-mix", conf
                return "hi", conf

            if lang == "en":
                if dev_ratio > 0.10:
                    return "code-mix", conf
                return "en", conf
    except Exception:
        pass

    # final heuristic
    if DEVANAGARI_RE.search(text) and LATIN_RE.search(text):
        return "code-mix", 0.55
    if DEVANAGARI_RE.search(text):
        return "hi", 0.55
    return "en", 0.50


def parse_transcript(text: str) -> List[Dict[str, Any]]:
    lines = [normalize_text(x) for x in text.splitlines() if x.strip()]
    utterances: List[Dict[str, Any]] = []

    for line in lines:
        m = SPEAKER_RE.match(line)
        if m:
            speaker = m.group(1).strip()
            content = m.group(2).strip()
        else:
            speaker = "Unknown"
            content = line

        lang, conf = detect_language_hint(content)
        dev_ratio, lat_ratio = _script_ratio(content)

        utterances.append(
            {
                "speaker": speaker,
                "text": content,
                "language_hint": lang,
                "language_confidence": round(conf, 3),
                "script_ratio": {
                    "devanagari": round(dev_ratio, 3),
                    "latin": round(lat_ratio, 3),
                },
            }
        )

    return utterances