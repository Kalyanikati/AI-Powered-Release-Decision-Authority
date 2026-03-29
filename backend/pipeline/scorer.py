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
                "top_risk_drivers": ["No decisions extracted"],
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

    total_penalty = owner_penalty + deadline_penalty + ambiguity_penalty + conflict_penalty
    score = max(0, 100 - total_penalty)

    if score >= 75:
        label = "Low Risk"
    elif score >= 50:
        label = "Medium Risk"
    else:
        label = "High Risk"

    top_risk_drivers = []
    if missing_owner > 0:
        top_risk_drivers.append(f"Missing owner in {missing_owner} decision(s)")
    if missing_deadline > 0:
        top_risk_drivers.append(f"Missing deadline in {missing_deadline} decision(s)")
    if ambiguity_count > 0:
        top_risk_drivers.append(f"Ambiguity flags: {ambiguity_count}")
    if conflict_count > 0:
        top_risk_drivers.append(f"Conflict pairs: {conflict_count}")

    if not top_risk_drivers:
        top_risk_drivers.append("No major structural risks found")

    return {
        "score": score,
        "label": label,
        "breakdown": {
            "decisions_count": total,
            "ambiguity_count": ambiguity_count,
            "conflict_count": conflict_count,
            "missing_owner": missing_owner,
            "missing_deadline": missing_deadline,
            "top_risk_drivers": top_risk_drivers[:3],
            "penalties": {
                "owner_penalty": owner_penalty,
                "deadline_penalty": deadline_penalty,
                "ambiguity_penalty": ambiguity_penalty,
                "conflict_penalty": conflict_penalty,
            },
        },
    }