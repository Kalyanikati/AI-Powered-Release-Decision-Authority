import re
from typing import Any, Dict, List, Set

STOP = {
    "the",
    "a",
    "an",
    "to",
    "for",
    "of",
    "and",
    "is",
    "will",
    "by",
    "on",
    "in",
    "we",
    "team",
    "this",
    "that",
    "it",
}
NEGATIONS = {"not", "nahi", "nahin", "no", "wont", "cannot"}


def detect_conflicts(decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    conflicts: List[Dict[str, Any]] = []

    for i in range(len(decisions)):
        for j in range(i + 1, len(decisions)):
            d1, d2 = decisions[i], decisions[j]
            s1 = d1.get("decision") or ""
            s2 = d2.get("decision") or ""

            if not _same_topic(s1, s2):
                continue

            owner1 = (d1.get("owner") or "").strip().lower()
            owner2 = (d2.get("owner") or "").strip().lower()
            if owner1 and owner2 and owner1 != owner2:
                conflicts.append(
                    {
                        "statement1": d1.get("quote") or s1,
                        "statement2": d2.get("quote") or s2,
                        "reason": "owner conflict",
                        "severity": "high",
                    }
                )

            dl1 = (d1.get("deadline") or "").strip().lower()
            dl2 = (d2.get("deadline") or "").strip().lower()
            if dl1 and dl2 and dl1 != dl2:
                conflicts.append(
                    {
                        "statement1": d1.get("quote") or s1,
                        "statement2": d2.get("quote") or s2,
                        "reason": "deadline conflict",
                        "severity": "medium",
                    }
                )

            b1 = f"{s1} {(d1.get('quote') or '')}".lower()
            b2 = f"{s2} {(d2.get('quote') or '')}".lower()
            n1 = any(n in b1 for n in NEGATIONS)
            n2 = any(n in b2 for n in NEGATIONS)
            if n1 != n2:
                conflicts.append(
                    {
                        "statement1": d1.get("quote") or s1,
                        "statement2": d2.get("quote") or s2,
                        "reason": "intent conflict",
                        "severity": "medium",
                    }
                )

    return _unique(conflicts)


def _tokens(text: str) -> Set[str]:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {w for w in words if w not in STOP and len(w) > 2}


def _same_topic(a: str, b: str) -> bool:
    ta = _tokens(a)
    tb = _tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) >= 2


def _unique(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for x in items:
        k = (x.get("statement1"), x.get("statement2"), x.get("reason"))
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out