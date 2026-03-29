from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pipeline.graph_flow import build_graph
from pipeline.approval_store import APPROVAL_STORE
from pipeline.request_parser import parse_raw_request

app = FastAPI(title="SDLC Governance Copilot - Release Approvals")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hackathon mode
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = build_graph()


class ReleaseRequest(BaseModel):
    request_id: Optional[str] = None
    requester_name: str
    requester_role: str = Field(description="developer|tech_lead")
    service_name: str
    environment: str = Field(description="staging|production")
    change_type: str = Field(description="release|hotfix")
    urgency: str = Field(description="normal|high|critical")
    planned_window: str

    has_test_evidence: bool
    has_security_scan: bool
    has_rollback_plan: bool

    db_change: bool = False
    pii_impact: bool = False
    notes: str = ""


class ApprovalDecision(BaseModel):
    decision: str = Field(description="approve|reject")
    comment: str = ""
    approver_name: str
    approver_role: str = Field(
        description="release_manager|security_reviewer|compliance_reviewer"
    )


class RawTextRequest(BaseModel):
    raw_text: str


@app.get("/")
def root() -> Dict[str, str]:
    return {"message": "SDLC Governance Copilot backend running"}


@app.post("/release-requests")
def submit_release_request(req: ReleaseRequest) -> Dict[str, Any]:
    try:
        state = graph.invoke(req.model_dump())

        if state.get("status") == "needs_human_approval":
            approval_id = state.get("approval_id")
            if approval_id:
                APPROVAL_STORE[approval_id] = state

        return state
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/approvals/queue")
def get_approval_queue() -> List[Dict[str, Any]]:
    queue = []
    for approval_id, item in APPROVAL_STORE.items():
        if item.get("status") == "needs_human_approval":
            queue.append(
                {
                    "approval_id": approval_id,
                    "request_id": item.get("request_id"),
                    "service_name": item.get("service_name"),
                    "change_type": item.get("change_type"),
                    "risk_label": item.get("risk_label"),
                    "risk_score": item.get("risk_score"),
                    "required_approver": item.get("required_approver"),
                    "policy_violations": item.get("policy_violations", []),
                    "escalation_reason": item.get("escalation_reason", ""),
                }
            )
    return queue


@app.get("/approvals/{approval_id}")
def get_approval_detail(approval_id: str) -> Dict[str, Any]:
    item = APPROVAL_STORE.get(approval_id)
    if not item:
        raise HTTPException(status_code=404, detail="Approval id not found")
    return item


@app.post("/approvals/{approval_id}/decision")
def submit_approval_decision(approval_id: str, req: ApprovalDecision) -> Dict[str, Any]:
    item = APPROVAL_STORE.get(approval_id)
    if not item:
        raise HTTPException(status_code=404, detail="Approval id not found")

    decision = req.decision.lower().strip()
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="decision must be approve or reject")

    item["approver_name"] = req.approver_name
    item["approver_role"] = req.approver_role
    item["approval_comment"] = req.comment
    item["human_decision"] = decision
    item["status"] = "approved_by_human" if decision == "approve" else "rejected_by_human"

    APPROVAL_STORE[approval_id] = item
    return item


@app.post("/parse-request")
def parse_raw_text(req: RawTextRequest) -> Dict[str, Any]:
    try:
        return parse_raw_request(req.raw_text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))