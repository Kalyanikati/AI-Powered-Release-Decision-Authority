from typing import Any, Dict, List


def compute_score(
    decisions: List[Dict[str, Any]],
    ambiguities: List[Dict[str, Any]],
    conflicts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not decisions:
        return {
            "score": 0,
            "label": "High Risk",
            "breakdown": {
                "decisions_count": 0,
                "ambiguity_count": 0,
                "conflict_count": 0,
                "missing_owner": 0,
                "missing_deadline": 0,
                "penalties": {"no_decisions": 100},
            },
        }

    total = len(decisions)
    missing_owner = sum(1 for d in decisions if not d.get("owner"))
    missing_deadline = sum(1 for d in decisions if not d.get("deadline"))
    ambiguity_count = len(ambiguities)
    conflict_count = len(conflicts)

    owner_penalty = round((missing_owner / total) * 30)
    deadline_penalty = round((missing_deadline / total) * 25)
    ambiguity_penalty = min(ambiguity_count * 8, 24)
    conflict_penalty = min(conflict_count * 15, 30)

    score = max(0, 100 - owner_penalty - deadline_penalty - ambiguity_penalty - conflict_penalty)

    if score >= 75:
        label = "Low Risk"
    elif score >= 50:
        label = "Medium Risk"
    else:
        label = "High Risk"

    return {
        "score": score,
        "label": label,
        "breakdown": {
            "decisions_count": total,
            "ambiguity_count": ambiguity_count,
            "conflict_count": conflict_count,
            "missing_owner": missing_owner,
            "missing_deadline": missing_deadline,
            "penalties": {
                "owner_penalty": owner_penalty,
                "deadline_penalty": deadline_penalty,
                "ambiguity_penalty": ambiguity_penalty,
                "conflict_penalty": conflict_penalty,
            },
        },
    }