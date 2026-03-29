import os
from pathlib import Path
from typing import Any, Dict, List

from sklearn.metrics.pairwise import cosine_similarity


DEFAULT_MARKERS = [
    "maybe",
    "probably",
    "possibly",
    "soon",
    "later",
    "not sure",
    "we will try",
    "asap",
    "around",
    "sometime",
    "tbd",
    "shayad",
    "jaldi",
    "baad mein",
    "pata nahi",
    "dekhte hain",
    "ho jayega",
]

DEADLINE_VAGUE = ["soon", "later", "asap", "jaldi", "baad mein", "sometime"]
_EMBED_MODEL = None


def detect_ambiguity(decisions: List[Dict[str, Any]], project_root: str) -> List[Dict[str, Any]]:
    markers = _load_markers(project_root)
    flags: List[Dict[str, Any]] = []

    semantic_enabled = os.getenv("USE_SEMANTIC_AMBIGUITY", "1") == "1"
    semantic_threshold = float(os.getenv("SEMANTIC_THRESHOLD", "0.56"))

    for d in decisions:
        decision_text = (d.get("decision") or "").strip()
        quote = (d.get("quote") or "").strip()
        blob = f"{decision_text} {quote}".lower()

        found_markers = [m for m in markers if m in blob]
        missing_owner = not d.get("owner")
        missing_deadline = not d.get("deadline")

        sem_hit = None
        sem_score = 0.0
        if semantic_enabled and decision_text:
            sem_hit, sem_score = _semantic_uncertainty_match(decision_text, markers)
            if sem_hit and sem_score >= semantic_threshold and sem_hit not in found_markers:
                found_markers.append(sem_hit)

        if found_markers or missing_owner or missing_deadline:
            reasons = []
            if found_markers:
                reasons.append("vague language")
            if missing_owner:
                reasons.append("missing owner")
            if missing_deadline:
                reasons.append("missing concrete deadline")

            severity = "low"
            if len(reasons) >= 2:
                severity = "medium"
            if (missing_owner and missing_deadline) or len(found_markers) >= 2:
                severity = "high"

            confidence = min(0.99, 0.45 + 0.1 * len(reasons) + sem_score * 0.4)

            flags.append(
                {
                    "phrase": found_markers[0] if found_markers else "structural ambiguity",
                    "quote": quote or decision_text,
                    "reasons": reasons,
                    "severity": severity,
                    "confidence": round(confidence, 3),
                }
            )

    return flags


def _load_markers(project_root: str) -> List[str]:
    root = Path(project_root)
    files = [
        root / "lexicons" / "uncertainty_en.txt",
        root / "lexicons" / "uncertainty_hi.txt",
    ]

    loaded = []
    for p in files:
        if p.exists():
            loaded.extend([x.strip().lower() for x in p.read_text().splitlines() if x.strip()])

    for x in DEADLINE_VAGUE:
        loaded.append(x)

    merged = sorted(set(DEFAULT_MARKERS + loaded))
    return merged


def _semantic_uncertainty_match(text: str, markers: List[str]):
    model = _get_embed_model()
    if model is None:
        return None, 0.0

    try:
        vec_text = model.encode([text])
        vec_markers = model.encode(markers)
        sims = cosine_similarity(vec_text, vec_markers)[0]
        idx = int(sims.argmax())
        return markers[idx], float(sims[idx])
    except Exception:
        return None, 0.0


def _get_embed_model():
    global _EMBED_MODEL
    if _EMBED_MODEL is not None:
        return _EMBED_MODEL
    try:
        from sentence_transformers import SentenceTransformer
        _EMBED_MODEL = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    except Exception:
        _EMBED_MODEL = False
    return _EMBED_MODEL if _EMBED_MODEL is not False else None