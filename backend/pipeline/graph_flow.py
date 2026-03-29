from typing import Any, Dict, List, TypedDict
from uuid import uuid4

from langgraph.graph import END, StateGraph

from .policy_store import retrieve_relevant_policies


class ReleaseState(TypedDict, total=False):
    request_id: str
    requester_name: str
    requester_role: str
    service_name: str
    environment: str
    change_type: str
    urgency: str
    planned_window: str
    has_test_evidence: bool
    has_security_scan: bool
    has_rollback_plan: bool
    db_change: bool
    pii_impact: bool
    notes: str

    required_checks: List[str]
    policy_violations: List[str]
    retrieved_policies: List[Dict[str, Any]]
    risk_score: int
    risk_label: str

    status: str
    escalation_reason: str
    required_approver: str
    approval_id: str
    decision_summary: str
    decision_details: Dict[str, Any]

    audit_log: List[Dict[str, Any]]


def normalize_node(state: ReleaseState) -> ReleaseState:
    out: ReleaseState = dict(state)

    if not out.get("request_id"):
        out["request_id"] = str(uuid4())

    out["requester_role"] = (out.get("requester_role") or "").lower()
    out["environment"] = (out.get("environment") or "").lower()
    out["change_type"] = (out.get("change_type") or "").lower()
    out["urgency"] = (out.get("urgency") or "").lower()

    out["audit_log"] = [
        {
            "event": "request_received",
            "by": out.get("requester_name", "unknown"),
        }
    ]
    return out


def policy_check_node(state: ReleaseState) -> ReleaseState:
    checks: List[str] = []
    violations: List[str] = []

    env = state.get("environment", "")
    change_type = state.get("change_type", "")

    # Build RAG query from release context
    query_parts = [
        f"environment {env}",
        f"change type {change_type}",
        f"urgency {state.get('urgency', '')}",
    ]
    if state.get("db_change"):
        query_parts.append("database schema change")
    if state.get("pii_impact"):
        query_parts.append("PII personal data impact")
    if not state.get("has_security_scan"):
        query_parts.append("no security scan completed")
    if not state.get("has_rollback_plan"):
        query_parts.append("no rollback plan provided")
    if not state.get("has_test_evidence"):
        query_parts.append("missing test evidence coverage")

    retrieved_policies = retrieve_relevant_policies(" ".join(query_parts), n_results=3)

    # Deterministic policy checks grounded by retrieved policy docs
    checks.append("test_evidence_required")
    if not state.get("has_test_evidence"):
        violations.append("Missing test evidence")

    if env == "production":
        checks.append("rollback_plan_required")
        if not state.get("has_rollback_plan"):
            violations.append("Missing rollback plan for production")

        checks.append("security_scan_required")
        if not state.get("has_security_scan"):
            violations.append("Missing security scan for production")

    if state.get("db_change"):
        checks.append("db_change_review_required")
        if not state.get("has_rollback_plan"):
            violations.append("DB change without rollback confidence")

    if state.get("pii_impact"):
        checks.append("compliance_review_required")
        if not state.get("has_security_scan"):
            violations.append("PII-impacting change without security scan")

    if change_type == "hotfix" and state.get("urgency") == "critical":
        checks.append("post_release_review_required")

    return {
        "required_checks": checks,
        "policy_violations": violations,
        "retrieved_policies": retrieved_policies,
        "audit_log": state.get("audit_log", []) + [
            {
                "event": "policy_checked",
                "rag_policies_retrieved": retrieved_policies,
            }
        ],
    }


def risk_score_node(state: ReleaseState) -> ReleaseState:
    score = 10

    if state.get("environment") == "production":
        score += 25
    if state.get("change_type") == "hotfix":
        score += 15
    if state.get("urgency") in {"high", "critical"}:
        score += 10
    if state.get("db_change"):
        score += 20
    if state.get("pii_impact"):
        score += 20

    score += min(20, len(state.get("policy_violations", [])) * 10)
    score = min(100, score)

    if score >= 70:
        label = "high"
    elif score >= 40:
        label = "medium"
    else:
        label = "low"

    return {
        "risk_score": score,
        "risk_label": label,
        "audit_log": state.get("audit_log", []) + [{"event": "risk_scored", "score": score, "label": label}],
    }


def route_node(state: ReleaseState) -> ReleaseState:
    score = state.get("risk_score", 0)
    violations = state.get("policy_violations", [])
    env = state.get("environment", "")
    retrieved_policies = state.get("retrieved_policies", [])

    needs_human = (score >= 40) or (len(violations) > 0) or (env == "production")

    if not needs_human:
        # AUTO-APPROVED PATH — Full decision details
        return {
            "status": "auto_approved",
            "required_approver": "none",
            "approval_id": None,
            "escalation_reason": "",
            "decision_summary": f"✅ Auto-approved. Risk score {score}/100 ({state.get('risk_label')}), 0 violations, no escalation triggers met.",
            "decision_details": {
                "reason": "Risk score is below threshold, no policy violations detected, non-production environment",
                "checks_passed": state.get("required_checks", []),
                "risk_assessment": {
                    "score": score,
                    "label": state.get("risk_label"),
                    "factors": {
                        "environment": env,
                        "change_type": state.get("change_type"),
                        "urgency": state.get("urgency"),
                        "has_test_evidence": state.get("has_test_evidence"),
                        "has_security_scan": state.get("has_security_scan"),
                        "has_rollback_plan": state.get("has_rollback_plan"),
                        "db_change": state.get("db_change"),
                        "pii_impact": state.get("pii_impact"),
                    }
                },
                "applicable_policies": [p["policy"] for p in retrieved_policies],
            },
            "audit_log": state.get("audit_log", []) + [
                {
                    "event": "auto_approved_by_policy_gate",
                    "reason": "risk_below_threshold",
                    "policies_checked": len(retrieved_policies),
                }
            ],
        }

    # ESCALATION PATH — Full escalation details
    approver = "release_manager"
    if state.get("pii_impact"):
        approver = "compliance_reviewer"
    elif (not state.get("has_security_scan")) or state.get("db_change"):
        approver = "security_reviewer"

    approval_id = str(uuid4())

    escalation_reasons = []
    if score >= 40:
        escalation_reasons.append(f"risk score {score}/100 exceeds threshold of 40")
    if len(violations) > 0:
        escalation_reasons.append(f"{len(violations)} policy violation(s)")
    if env == "production":
        escalation_reasons.append("production environment requires human approval")

    reason = f"Escalated: {', '.join(escalation_reasons)}"

    return {
        "status": "needs_human_approval",
        "required_approver": approver,
        "approval_id": approval_id,
        "escalation_reason": reason,
        "decision_summary": f"⚠️ Escalated to {approver}. Risk {score}/100 ({state.get('risk_label')}), {len(violations)} violation(s) found.",
        "decision_details": {
            "reason": reason,
            "required_checks": state.get("required_checks", []),
            "policy_violations": violations,
            "risk_assessment": {
                "score": score,
                "label": state.get("risk_label"),
                "factors": {
                    "environment": env,
                    "change_type": state.get("change_type"),
                    "urgency": state.get("urgency"),
                    "has_test_evidence": state.get("has_test_evidence"),
                    "has_security_scan": state.get("has_security_scan"),
                    "has_rollback_plan": state.get("has_rollback_plan"),
                    "db_change": state.get("db_change"),
                    "pii_impact": state.get("pii_impact"),
                }
            },
            "applicable_policies": [p["policy"] for p in retrieved_policies],
            "approver_routing": {
                "assigned_to": approver,
                "reason": "pii_impact" if state.get("pii_impact") else ("security_concern" if (not state.get("has_security_scan")) or state.get("db_change") else "default_release_manager"),
            }
        },
        "audit_log": state.get("audit_log", []) + [
            {
                "event": "escalated_to_human",
                "approver": approver,
                "violations_count": len(violations),
                "risk_score": score,
                "policies_retrieved": len(retrieved_policies),
            }
        ],
    }


def build_graph():
    graph = StateGraph(ReleaseState)

    graph.add_node("normalize", normalize_node)
    graph.add_node("policy_check", policy_check_node)
    graph.add_node("risk_score", risk_score_node)
    graph.add_node("route", route_node)

    graph.set_entry_point("normalize")
    graph.add_edge("normalize", "policy_check")
    graph.add_edge("policy_check", "risk_score")
    graph.add_edge("risk_score", "route")
    graph.add_edge("route", END)

    return graph.compile()