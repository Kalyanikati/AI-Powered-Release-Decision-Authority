from typing import Any, Dict, List, Literal, TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from .policy_store import retrieve_relevant_policies
from .ai_rationale import generate_ai_rationale


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

    ai_rationale: str

    route_key: Literal["auto", "human"]
    status: str
    escalation_reason: str
    required_approver: str
    approval_id: str

    human_decision: str
    approver_name: str
    approver_role: str
    approval_comment: str

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

    out["audit_log"] = out.get("audit_log", []) + [
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
        "audit_log": state.get("audit_log", []) + [
            {"event": "risk_scored", "score": score, "label": label}
        ],
    }


def ai_rationale_node(state: ReleaseState) -> ReleaseState:
    rationale = generate_ai_rationale(
        service_name=state.get("service_name", "unknown"),
        environment=state.get("environment", ""),
        change_type=state.get("change_type", ""),
        urgency=state.get("urgency", ""),
        risk_score=state.get("risk_score", 0),
        risk_label=state.get("risk_label", ""),
        policy_violations=state.get("policy_violations", []),
        retrieved_policies=[p["policy"] for p in state.get("retrieved_policies", [])],
        has_test_evidence=state.get("has_test_evidence", False),
        has_security_scan=state.get("has_security_scan", False),
        has_rollback_plan=state.get("has_rollback_plan", False),
        db_change=state.get("db_change", False),
        pii_impact=state.get("pii_impact", False),
    )
    return {
        "ai_rationale": rationale,
        "audit_log": state.get("audit_log", []) + [
            {"event": "ai_rationale_generated", "length": len(rationale)}
        ],
    }


def route_node(state: ReleaseState) -> ReleaseState:
    score = state.get("risk_score", 0)
    violations = state.get("policy_violations", [])
    env = state.get("environment", "")

    needs_human = (score >= 40) or (len(violations) > 0) or (env == "production")

    if not needs_human:
        return {
            "route_key": "auto",
            "status": "ready_for_auto_finalize",
            "required_approver": "none",
            "escalation_reason": "",
            "audit_log": state.get("audit_log", []) + [{"event": "routed_auto"}],
        }

    approver = "release_manager"
    if state.get("pii_impact"):
        approver = "compliance_reviewer"
    elif (not state.get("has_security_scan")) or state.get("db_change"):
        approver = "security_reviewer"

    escalation_reasons: List[str] = []
    if score >= 40:
        escalation_reasons.append(f"risk score {score}/100 exceeds threshold of 40")
    if len(violations) > 0:
        escalation_reasons.append(f"{len(violations)} policy violation(s)")
    if env == "production":
        escalation_reasons.append("production environment requires human approval")

    reason = f"Escalated: {', '.join(escalation_reasons)}"

    return {
        "route_key": "human",
        "status": "awaiting_human_approval",
        "required_approver": approver,
        "approval_id": state.get("request_id", str(uuid4())),
        "escalation_reason": reason,
        "audit_log": state.get("audit_log", []) + [
            {"event": "routed_human", "required_approver": approver}
        ],
    }


def route_selector(state: ReleaseState) -> str:
    return "human" if state.get("route_key") == "human" else "auto"


def human_approval_node(state: ReleaseState) -> ReleaseState:
    approval_prompt = {
        "approval_id": state.get("approval_id"),
        "required_approver": state.get("required_approver"),
        "risk_score": state.get("risk_score"),
        "risk_label": state.get("risk_label"),
        "policy_violations": state.get("policy_violations", []),
        "escalation_reason": state.get("escalation_reason", ""),
        "ai_rationale": state.get("ai_rationale", ""),
    }

    human_input = interrupt(approval_prompt)

    decision = (human_input.get("decision") or "").lower().strip()
    if decision not in {"approve", "reject"}:
        decision = "reject"

    return {
        "human_decision": decision,
        "approver_name": (human_input.get("approver_name") or "").strip(),
        "approver_role": (human_input.get("approver_role") or "").strip(),
        "approval_comment": (human_input.get("comment") or "").strip(),
        "audit_log": state.get("audit_log", []) + [
            {
                "event": "human_decision_received",
                "decision": decision,
                "approver_name": (human_input.get("approver_name") or "").strip(),
                "approver_role": (human_input.get("approver_role") or "").strip(),
            }
        ],
    }


def finalize_auto_node(state: ReleaseState) -> ReleaseState:
    score = state.get("risk_score", 0)
    label = state.get("risk_label", "low")
    retrieved_policies = state.get("retrieved_policies", [])

    return {
        "status": "auto_approved",
        "required_approver": "none",
        "approval_id": None,
        "decision_summary": f"✅ Auto-approved. Risk score {score}/100 ({label}), no escalation triggers met.",
        "decision_details": {
            "reason": "Risk score below threshold, no policy violations, non-production",
            "checks_passed": state.get("required_checks", []),
            "risk_assessment": {"score": score, "label": label},
            "applicable_policies": [p["policy"] for p in retrieved_policies],
            "ai_rationale": state.get("ai_rationale", ""),
        },
        "audit_log": state.get("audit_log", []) + [
            {
                "event": "auto_approved_by_policy_gate",
                "reason": "risk_below_threshold",
                "policies_checked": len(retrieved_policies),
            }
        ],
    }


def finalize_human_node(state: ReleaseState) -> ReleaseState:
    score = state.get("risk_score", 0)
    label = state.get("risk_label", "low")
    violations = state.get("policy_violations", [])
    decision = state.get("human_decision", "reject")
    retrieved_policies = state.get("retrieved_policies", [])

    final_status = "approved_by_human" if decision == "approve" else "rejected_by_human"

    return {
        "status": final_status,
        "decision_summary": (
            f"{'✅' if decision == 'approve' else '❌'} "
            f"Escalated request {decision}d by {state.get('approver_name', 'reviewer')}."
        ),
        "decision_details": {
            "reason": state.get("escalation_reason", ""),
            "required_checks": state.get("required_checks", []),
            "policy_violations": violations,
            "risk_assessment": {"score": score, "label": label},
            "applicable_policies": [p["policy"] for p in retrieved_policies],
            "ai_rationale": state.get("ai_rationale", ""),
            "human_decision": {
                "decision": decision,
                "approver_name": state.get("approver_name", ""),
                "approver_role": state.get("approver_role", ""),
                "comment": state.get("approval_comment", ""),
            },
        },
        "audit_log": state.get("audit_log", []) + [
            {
                "event": "finalized_after_human_review",
                "final_status": final_status,
            }
        ],
    }


def build_graph():
    checkpointer = MemorySaver()

    graph = StateGraph(ReleaseState)

    graph.add_node("normalize", normalize_node)
    graph.add_node("policy_check", policy_check_node)
    graph.add_node("risk_score", risk_score_node)
    graph.add_node("ai_rationale", ai_rationale_node)
    graph.add_node("route", route_node)
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("finalize_auto", finalize_auto_node)
    graph.add_node("finalize_human", finalize_human_node)

    graph.set_entry_point("normalize")
    graph.add_edge("normalize", "policy_check")
    graph.add_edge("policy_check", "risk_score")
    graph.add_edge("risk_score", "ai_rationale")
    graph.add_edge("ai_rationale", "route")

    graph.add_conditional_edges(
        "route",
        route_selector,
        {
            "auto": "finalize_auto",
            "human": "human_approval",
        },
    )

    graph.add_edge("human_approval", "finalize_human")
    graph.add_edge("finalize_auto", END)
    graph.add_edge("finalize_human", END)

    return graph.compile(checkpointer=checkpointer)