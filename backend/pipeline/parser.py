import re
import unicodedata
from typing import Dict, List

SPEAKER_RE = re.compile(r"^\s*([A-Za-z0-9 _.\-]{1,40})\s*:\s*(.+)$")
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

HINGLISH_HINTS = {
    "kal",
    "aaj",
    "parso",
    "jaldi",
    "baad",
    "dekhte",
    "karenge",
    "ho jayega",
    "shayad",
    "pakka",
    "nahi",
    "haan",
    "thik",
    "deadline",
}


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip()


def detect_language_hint(text: str) -> str:
    t = text.lower()
    if DEVANAGARI_RE.search(t):
        return "hi"
    hint_count = sum(1 for h in HINGLISH_HINTS if h in t)
    if hint_count >= 2:
        return "code-mix"
    return "en"


def parse_transcript(text: str) -> List[Dict[str, str]]:
    lines = [normalize_text(x) for x in text.splitlines() if x.strip()]
    utterances = []

    for line in lines:
        m = SPEAKER_RE.match(line)
        if m:
            speaker = m.group(1).strip()
            content = m.group(2).strip()
        else:
            speaker = "Unknown"
            content = line

        utterances.append(
            {
                "speaker": speaker,
                "text": content,
                "language_hint": detect_language_hint(content),
            }
        )

    return utterances