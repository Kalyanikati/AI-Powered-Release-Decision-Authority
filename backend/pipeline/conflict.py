import os
import re
from typing import Any, Dict, List, Set

STOP = {
    "the", "a", "an", "to", "for", "of", "and", "is", "will", "by", "on", "in",
    "we", "team", "this", "that", "it", "hai", "ka", "ki"
}
NEGATIONS = {"not", "nahi", "nahin", "no", "cannot", "wont", "won't"}

_NLI_PIPE = None


def detect_conflicts(decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    conflicts: List[Dict[str, Any]] = []
    use_nli = os.getenv("USE_NLI_CONFLICT", "1") == "1"

    for i in range(len(decisions)):
        for j in range(i + 1, len(decisions)):
            d1, d2 = decisions[i], decisions[j]

            s1 = (d1.get("decision") or "").strip()
            s2 = (d2.get("decision") or "").strip()
            if not s1 or not s2:
                continue

            if not _same_topic(s1, s2):
                continue

            q1 = d1.get("quote") or s1
            q2 = d2.get("quote") or s2

            # owner conflict
            o1 = (d1.get("owner") or "").strip().lower()
            o2 = (d2.get("owner") or "").strip().lower()
            if o1 and o2 and o1 != o2:
                conflicts.append(
                    {
                        "statement1": q1,
                        "statement2": q2,
                        "reason": "owner conflict",
                        "severity": "high",
                        "confidence": 0.92,
                    }
                )

            # deadline conflict
            dl1 = (d1.get("deadline") or "").strip().lower()
            dl2 = (d2.get("deadline") or "").strip().lower()
            if dl1 and dl2 and dl1 != dl2:
                conflicts.append(
                    {
                        "statement1": q1,
                        "statement2": q2,
                        "reason": "deadline conflict",
                        "severity": "medium",
                        "confidence": 0.86,
                    }
                )

            # intent conflict by negation mismatch
            b1 = f"{s1} {q1}".lower()
            b2 = f"{s2} {q2}".lower()
            n1 = any(n in b1 for n in NEGATIONS)
            n2 = any(n in b2 for n in NEGATIONS)
            if n1 != n2:
                conflicts.append(
                    {
                        "statement1": q1,
                        "statement2": q2,
                        "reason": "intent conflict",
                        "severity": "medium",
                        "confidence": 0.78,
                    }
                )

            # optional NLI contradiction
            if use_nli:
                c_score = _nli_contradiction_score(q1, q2)
                if c_score >= 0.72:
                    conflicts.append(
                        {
                            "statement1": q1,
                            "statement2": q2,
                            "reason": "intent conflict",
                            "severity": "medium",
                            "confidence": round(c_score, 3),
                        }
                    )

    return _unique(conflicts)


def _tokens(text: str) -> Set[str]:
    words = re.findall(r"[A-Za-z0-9]+", text.lower())
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


def _get_nli_pipeline():
    global _NLI_PIPE
    if _NLI_PIPE is not None:
        return _NLI_PIPE
    try:
        from transformers import pipeline
        _NLI_PIPE = pipeline(
            "text-classification",
            model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
            top_k=None,
        )
    except Exception:
        _NLI_PIPE = False
    return _NLI_PIPE if _NLI_PIPE is not False else None


def _nli_contradiction_score(a: str, b: str) -> float:
    nli = _get_nli_pipeline()
    if nli is None:
        return 0.0
    try:
        result = nli(f"{a} </s></s> {b}")
        if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
            preds = result[0]
        else:
            preds = result if isinstance(result, list) else []

        score = 0.0
        for p in preds:
            label = p.get("label", "").lower()
            if "contradiction" in label:
                score = max(score, float(p.get("score", 0.0)))
        return score
    except Exception:
        return 0.0