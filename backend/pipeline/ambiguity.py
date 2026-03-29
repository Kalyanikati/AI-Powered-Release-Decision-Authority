from pathlib import Path
from typing import Any, Dict, List

DEFAULT_MARKERS = [
    "maybe",
    "probably",
    "possibly",
    "soon",
    "later",
    "not sure",
    "we should",
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
    "try karte",
]


def detect_ambiguity(decisions: List[Dict[str, Any]], project_root: str) -> List[Dict[str, Any]]:
    markers = _load_markers(project_root)
    flags: List[Dict[str, Any]] = []

    for d in decisions:
        decision_text = (d.get("decision") or "").lower()
        quote = (d.get("quote") or "").lower()
        blob = f"{decision_text} {quote}"

        found = [m for m in markers if m in blob]
        missing_owner = not d.get("owner")
        missing_deadline = not d.get("deadline")

        if found or missing_owner or missing_deadline:
            reasons = []
            if found:
                reasons.append("vague language")
            if missing_owner:
                reasons.append("missing owner")
            if missing_deadline:
                reasons.append("missing concrete deadline")

            severity = "low"
            if len(reasons) >= 2:
                severity = "medium"
            if missing_owner and missing_deadline:
                severity = "high"

            flags.append(
                {
                    "phrase": found[0] if found else "structural ambiguity",
                    "quote": d.get("quote") or d.get("decision") or "",
                    "reasons": reasons,
                    "severity": severity,
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
            lines = [x.strip().lower() for x in p.read_text().splitlines() if x.strip()]
            loaded.extend(lines)

    merged = sorted(set(DEFAULT_MARKERS + loaded))
    return merged