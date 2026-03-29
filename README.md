```markdown
# SDLC Governance Copilot

AI-powered release request governance system with LangGraph orchestration, RAG-backed policy retrieval, and human-in-the-loop approval flow.

Built for ET GenAI Hackathon Phase 2.

## Problem Statement

Enterprise software releases fail governance checks due to:
- manual, inconsistent policy reviews
- release requests buried in Slack messages, emails, and JIRA comments
- no structured risk scoring before deployment
- approval bottlenecks with no audit trail
- policy knowledge scattered across wikis and runbooks

Most existing tools handle ticketing or CI/CD, but none enforce SDLC governance policy as an intelligent, explainable AI layer grounded in organization-specific policy documents.

## Solution Overview

SDLC Governance Copilot transforms unstructured release requests into governed, policy-checked, risk-scored approval workflows using LangGraph orchestration and RAG-backed policy retrieval.

Core capabilities:
- raw text intake from Slack, email, or JIRA — parsed by Groq LLM into structured release request fields
- LangGraph StateGraph multi-node pipeline: normalize → policy_check → risk_score → route
- **RAG-backed policy retrieval** — semantic search over SDLC policy documents to retrieve context-relevant governance rules
- deterministic policy gate with explainable violations grounded in retrieved policies
- automated routing to the correct approver (release manager, security reviewer, compliance reviewer)
- human-in-the-loop approval queue with full audit trail
- complete audit log on every decision (auto-approved or escalated)

## Architecture

```
Raw Text (Slack / Email / JIRA)
        ↓
  LLM Parser (Groq)
        ↓
  Structured Release Request
        ↓
  LangGraph Pipeline
    ├── normalize_node
    │   └─ standardise fields, assign request_id
    │
    ├── policy_check_node
    │   ├─ Build semantic query from release context
    │   ├─ **RAG Retrieval** — query ChromaDB vector store
    │   ├─ retrieve top-3 relevant policy docs
    │   └─ evaluate against deterministic policy rules
    │
    ├── risk_score_node
    │   └─ compute 0–100 risk score with label (low/medium/high)
    │
    └── route_node
        ├─ auto_approved (if risk < 40, no violations, non-production)
        └─ needs_human_approval (escalate + route to approver)
        ↓
  Human Approver Queue
  (approve / reject with comment)
        ↓
  Audit Log + Final Status
```

## Tech Stack

Frontend:
- React + Vite
- Plain CSS-in-JS (no external UI library)

Backend:
- FastAPI + Uvicorn
- LangGraph (StateGraph)
- ChromaDB (in-memory vector store with ONNX embeddings)
- Groq API — llama-3.3-70b-versatile
- python-dotenv
- Pydantic v2

## Repository Structure

```
et-decision-ui/
├── frontend/
│   └── src/
│       └── App.jsx               # 4-step UI: paste → auto-fill → submit → approve
├── backend/
│   ├── main.py                   # FastAPI entry point, all routes
│   ├── requirements.txt
│   ├── .env                      # GROQ_API_KEY (not committed)
│   └── pipeline/
│       ├── __init__.py
│       ├── graph_flow.py         # LangGraph StateGraph orchestration
│       ├── request_parser.py     # LLM raw text → structured fields
│       ├── policy_store.py       # ChromaDB vector store + RAG retrieval
│       └── approval_store.py     # In-memory approval queue
└── README.md
```

## Setup Instructions

Prerequisites:
- Node.js 18+
- Python 3.9+
- Groq API key (free tier at console.groq.com)

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:

```
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

Run backend:

```bash
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Default URLs

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

## API Contract

### Parse raw text to structured fields

```
POST /parse-request

Request:
{
  "raw_text": "Hi team, please approve release for payment-service..."
}

Response:
{
  "requester_name": "John Smith",
  "requester_role": "tech_lead",
  "service_name": "payment-service",
  "environment": "production",
  "change_type": "release",
  "urgency": "normal",
  "planned_window": "2026-03-29 02:00 UTC",
  "has_test_evidence": true,
  "has_security_scan": true,
  "has_rollback_plan": true,
  "db_change": false,
  "pii_impact": false,
  "notes": "..."
}
```

### Submit release request to policy gate

```
POST /release-requests

Request:
{
  "requester_name": "John Smith",
  "requester_role": "tech_lead",
  "service_name": "payment-service",
  "environment": "production",
  "change_type": "release",
  "urgency": "normal",
  "planned_window": "2026-03-29 02:00 UTC",
  "has_test_evidence": true,
  "has_security_scan": true,
  "has_rollback_plan": true,
  "db_change": false,
  "pii_impact": false,
  "notes": "Improved transaction handling and checkout flow fixes"
}

Response:
{
  "status": "auto_approved" | "needs_human_approval",
  "request_id": "uuid",
  "risk_score": 25,
  "risk_label": "low",
  "decision_summary": "✅ Auto-approved. Risk score 25/100 (low), 0 violations, no escalation triggers met.",
  "decision_details": {
    "reason": "Risk score is below threshold...",
    "checks_passed": [...],
    "risk_assessment": {...},
    "applicable_policies": ["Retrieved policy doc 1", "Retrieved policy doc 2", ...]
  },
  "policy_violations": [],
  "required_checks": ["test_evidence_required", ...],
  "required_approver": "none" | "release_manager" | "security_reviewer" | "compliance_reviewer",
  "approval_id": "uuid (if escalated)",
  "retrieved_policies": [
    {
      "id": "pol_001",
      "policy": "All production deployments require a security scan...",
      "relevance_score": 0.95
    },
    ...
  ],
  "audit_log": [
    {"event": "request_received", "by": "John Smith"},
    {"event": "policy_checked", "rag_policies_retrieved": [...]},
    {"event": "risk_scored", "score": 25, "label": "low"},
    {"event": "auto_approved_by_policy_gate", "reason": "risk_below_threshold", "policies_checked": 3}
  ]
}
```

### Approvals queue

```
GET  /approvals/queue
→ List of pending approval items

GET  /approvals/{approval_id}
→ Full approval details

POST /approvals/{approval_id}/decision
{
  "decision": "approve" | "reject",
  "approver_name": "Jane Doe",
  "approver_role": "security_reviewer",
  "comment": "Approved. Security scan looks good."
}
→ Updated approval with human decision recorded
```

## Policy Gate Logic

### Escalation Triggers

Any one of these triggers `needs_human_approval`:

1. **Risk score ≥ 40**
2. **Any policy violation detected**
3. **Environment is production**

### Policy Violations Detected

Violations are identified by comparing release request against retrieved and deterministic policies:

- Missing security scan on production or hotfix
- Missing rollback plan on production
- DB change without security scan or rollback plan
- PII-impacting change without security scan
- Critical urgency hotfix to production

### Approver Routing

| Condition | Assigned Approver |
|---|---|
| `pii_impact == true` | `compliance_reviewer` |
| `db_change == true` OR no security scan | `security_reviewer` |
| All others | `release_manager` |

## Risk Scoring

Score: 0–100 (higher = more risk)

| Factor | Points |
|---|---|
| production environment | +30 |
| hotfix change type | +20 |
| critical urgency | +15 |
| missing security scan | +15 |
| missing rollback plan | +10 |
| DB change | +10 |
| PII impact | +10 |
| missing test evidence | +5 |
| high urgency | +5 |
| each policy violation | +10 (max 20) |

Base score: 10. Final score capped at 100.

**Risk Labels:**

- `low`: 0–39
- `medium`: 40–69
- `high`: 70–100

## RAG Implementation

### Policy Document Store

12 pre-loaded SDLC policy clauses are embedded into an in-memory ChromaDB vector store using ONNX embeddings (auto-downloaded on first run).

Policy examples:

- "All production deployments require a security scan completed within 72 hours before release."
- "Any change to production environment must have a documented rollback plan approved by the team lead."
- "Database schema changes require a rollback migration script and must be reviewed by the DBA team."
- "Changes impacting PII data must have compliance team sign-off and a security scan before deployment."
- ... and 8 more

### Semantic Query

During `policy_check_node`, the system builds a semantic query from the release request context:

```
"environment production change type release urgency normal 
 security scan completed rollback plan provided test evidence coverage"
```

### Retrieval and Grounding

ChromaDB performs vector similarity search and returns the top-3 most relevant policy documents with relevance scores (0–1).

These retrieved policies are:

1. **Included in the response** under `retrieved_policies`
2. **Logged in audit_log** under `rag_policies_retrieved`
3. **Displayed in the frontend** in a dedicated "Applicable Policies (RAG Retrieved)" section

## Demo Flow

1. **Copy a release request** — Paste a Slack/email/JIRA message into Step 1
2. **Auto-parse** — Click "Parse & Auto-Fill Form", LLM extracts fields
3. **Review and submit** — Edit if needed, click "Submit Request"
4. **Policy gate fires** — LangGraph runs RAG retrieval + policy checks + risk scoring
5. **View decision** — Step 3 shows:
   - Decision summary (✅ auto-approved or ⚠️ escalated)
   - Risk score and violations
   - Retrieved policies from RAG
   - Full audit trail
6. **Approver decision** — If escalated, approver reviews in Step 4 and approves/rejects

### Example Scenarios

**Scenario A: Low-risk staging release → Auto-approved**

- Environment: staging
- Change type: release
- Has test evidence, security scan, rollback plan
- No DB/PII changes
- Urgency: normal

→ Risk = 10, no violations → **auto_approved** with ✅ summary

**Scenario B: Production hotfix without security scan → Escalated**

- Environment: production
- Change type: hotfix
- No security scan
- Urgency: high

→ Risk = 55, violations = ["Missing security scan for production"]
→ RAG retrieves "All production deployments require a security scan..."
→ **needs_human_approval** routed to **security_reviewer** with ⚠️ summary

## Current Limitations

- in-memory approval store (resets on server restart)
- no persistent database (PostgreSQL recommended for production)
- no authentication or role-based access control
- single-tenant, single-process design
- policy documents pre-loaded (not dynamically configurable)
- ChromaDB in-memory store (not persisted across restarts)

## Future Roadmap

- **Persistent storage** — PostgreSQL + SQLAlchemy for approvals and policy documents
- **Dynamic policy management** — UI to upload/update policy documents
- **Slack bot integration** — Native approval flow in Slack
- **CI/CD webhook triggers** — Automatically submit releases from CI/CD pipelines
- **Multi-tenant enterprise auth** — SSO/SAML
- **Trend analytics dashboard** — Metrics across release history (approval rates, risk distribution, etc.)
- **Policy version control** — Track policy document changes with audit trail
- **Team-specific policies** — Different policy sets per team or service

## One-line Positioning

We do not block releases — we make every release decision explainable, auditable, and policy-enforced using AI-powered semantic policy retrieval.

## Key Features Summary

| Feature | Details |
|---|---|
| **LLM Parsing** | Raw text → structured fields via Groq |
| **LangGraph Orchestration** | 4-node pipeline: normalize → policy_check (with RAG) → risk_score → route |
| **RAG Policy Retrieval** | ChromaDB vector search for context-relevant SDLC policies |
| **Policy Gate** | Deterministic rules + retrieved policies = explainable violations |
| **Risk Scoring** | Weighted algorithm, 0–100 with low/medium/high labels |
| **Auto-Approval** | Sub-40 risk + no violations + non-production = auto-approved |
| **HITL Approval Queue** | Human-in-the-loop for escalated requests with full audit trail |
| **Approver Routing** | Intelligent routing based on PII, DB changes, security concerns |
| **Full Audit Trail** | Every decision step logged with timestamp, policy refs, and reasoning |

## Contact & Support

Built as a hackathon prototype. For questions or contributions, open an issue in the repository.
```

Copy and paste this entire content into your `README.md` file.Copy and paste this entire content into your `README.md` file.