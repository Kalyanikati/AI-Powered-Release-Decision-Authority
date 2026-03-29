import { useEffect, useState } from "react";

const API_BASE = "http://localhost:8000";

const initialForm = {
  requester_name: "",
  requester_role: "developer",
  service_name: "",
  environment: "production",
  change_type: "release",
  urgency: "normal",
  planned_window: "",
  has_test_evidence: false,
  has_security_scan: false,
  has_rollback_plan: false,
  db_change: false,
  pii_impact: false,
  notes: "",
};

const SAMPLE_RAW = `Hi team,

Please approve the following release for the payment-service.

Requester: John Smith (Tech Lead)
Service: payment-service
Environment: production
Change Type: release
Urgency: normal

Description:
We're releasing version 2.5.0 with improved transaction handling and bug fixes for the checkout flow.

PR Link: https://github.com/org/payment-service/pull/456
Test Coverage: 78% (unit tests added for new transaction validation)
Security Scan: Completed on 2026-03-29, no critical issues found
Rollback Plan: Documented in release runbook, validated by ops team

Database Changes: No schema changes
PII Impact: No - transaction IDs are not considered PII in our system
Monitoring Tools: DataDog, Prometheus
Monitoring Duration: 4 hours post-deployment

Release Window: 2026-03-29 02:00 UTC to 03:00 UTC (low-traffic window)
Rollback Duration: ~15 minutes

Release Notes: https://wiki.example.com/releases/payment-service-2.5.0`;

export default function App() {
  const [rawText, setRawText] = useState(SAMPLE_RAW);
  const [parsing, setParsing] = useState(false);
  const [parsedPreview, setParsedPreview] = useState(null);

  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [queue, setQueue] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [decisionForm, setDecisionForm] = useState({
    decision: "approve",
    comment: "",
    approver_name: "",
    approver_role: "release_manager",
  });

  async function parseRaw() {
    if (!rawText.trim()) return;
    setParsing(true);
    setError("");
    setParsedPreview(null);
    try {
      const res = await fetch(`${API_BASE}/parse-request`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_text: rawText }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Parse failed");
      setForm({ ...initialForm, ...data });
      setParsedPreview(data);
    } catch (err) {
      setError(err.message || "Parse failed");
    } finally {
      setParsing(false);
    }
  }

  async function submitRequest(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const payload = {
        requester_name: form.requester_name || "",
        requester_role: form.requester_role || "developer",
        service_name: form.service_name || "",
        environment: form.environment || "production",
        change_type: form.change_type || "release",
        urgency: form.urgency || "normal",
        planned_window: form.planned_window || "",
        has_test_evidence: Boolean(form.has_test_evidence),
        has_security_scan: Boolean(form.has_security_scan),
        has_rollback_plan: Boolean(form.has_rollback_plan),
        db_change: Boolean(form.db_change),
        pii_impact: Boolean(form.pii_impact),
        notes: form.notes || "",
      };
      const res = await fetch(`${API_BASE}/release-requests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Request failed");
      setResult(data);
      await loadQueue();
    } catch (err) {
      setError(err.message || "Unexpected error");
    } finally {
      setLoading(false);
    }
  }

  async function loadQueue() {
    try {
      const res = await fetch(`${API_BASE}/approvals/queue`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to load queue");
      setQueue(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn("Queue load:", err.message);
    }
  }

  async function submitDecision(approvalId) {
    try {
      const res = await fetch(`${API_BASE}/approvals/${approvalId}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(decisionForm),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Decision failed");
      setResult(data);
      await loadQueue();
    } catch (err) {
      setError(err.message || "Decision submit failed");
    }
  }

  useEffect(() => {
    loadQueue();
  }, []);

  const riskColor = {
    high: "#c53030",
    medium: "#b7791f",
    low: "#276749",
  };

  return (
    <div
      style={{
        maxWidth: 1100,
        margin: "20px auto",
        padding: 16,
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ margin: "0 0 4px" }}>SDLC Governance Copilot</h1>
        <p style={{ margin: 0, color: "#555" }}>
          AI-powered release request intake, policy gate, auto-approval, and
          human approver flow.
        </p>
      </div>

      {error ? (
        <div
          style={{
            border: "1px solid #ffb4b4",
            background: "#fff1f1",
            padding: 10,
            marginBottom: 12,
            borderRadius: 6,
          }}
        >
          {error}
        </div>
      ) : null}

      {/* STEP 1 */}
      <Section title="Step 1 — Paste Raw Release Request (Slack / Email / JIRA)">
        <textarea
          rows={8}
          style={{
            width: "100%",
            padding: 10,
            fontFamily: "monospace",
            fontSize: 13,
          }}
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          placeholder="Paste Slack message, email, or JIRA description here..."
        />
        <div
          style={{
            display: "flex",
            gap: 10,
            marginTop: 8,
            alignItems: "center",
          }}
        >
          <button
            type="button"
            onClick={parseRaw}
            disabled={parsing}
            style={{
              padding: "10px 16px",
              background: "#2b6cb0",
              color: "#fff",
              border: 0,
              borderRadius: 6,
              cursor: "pointer",
              fontWeight: 700,
            }}
          >
            {parsing ? "Parsing with AI..." : "Parse & Auto-Fill Form"}
          </button>
          {parsedPreview ? (
            <span style={{ color: "#276749", fontWeight: 600 }}>
              Form auto-filled from raw request
            </span>
          ) : null}
        </div>
      </Section>

      {/* STEP 2 */}
      <form onSubmit={submitRequest}>
        <Section title="Step 2 — Review & Submit Release Request">
          <Grid>
            <Input
              label="Requester Name"
              value={form.requester_name}
              onChange={(v) => setForm({ ...form, requester_name: v })}
            />
            <Select
              label="Requester Role"
              value={form.requester_role}
              onChange={(v) => setForm({ ...form, requester_role: v })}
              options={["developer", "tech_lead"]}
            />
            <Input
              label="Service Name"
              value={form.service_name}
              onChange={(v) => setForm({ ...form, service_name: v })}
            />
            <Select
              label="Environment"
              value={form.environment}
              onChange={(v) => setForm({ ...form, environment: v })}
              options={["staging", "production"]}
            />
            <Select
              label="Change Type"
              value={form.change_type}
              onChange={(v) => setForm({ ...form, change_type: v })}
              options={["release", "hotfix"]}
            />
            <Select
              label="Urgency"
              value={form.urgency}
              onChange={(v) => setForm({ ...form, urgency: v })}
              options={["normal", "high", "critical"]}
            />
          </Grid>
          <div style={{ marginTop: 10 }}>
            <Input
              label="Planned Window"
              value={form.planned_window}
              onChange={(v) => setForm({ ...form, planned_window: v })}
            />
          </div>
          <textarea
            rows={3}
            style={{ width: "100%", marginTop: 10, padding: 10 }}
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            placeholder="Notes / description of change"
          />
          <div style={{ marginTop: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
              Checklist
            </div>
            <Grid>
              <Check
                label="Test Evidence"
                checked={form.has_test_evidence}
                onChange={(v) => setForm({ ...form, has_test_evidence: v })}
              />
              <Check
                label="Security Scan"
                checked={form.has_security_scan}
                onChange={(v) => setForm({ ...form, has_security_scan: v })}
              />
              <Check
                label="Rollback Plan"
                checked={form.has_rollback_plan}
                onChange={(v) => setForm({ ...form, has_rollback_plan: v })}
              />
              <Check
                label="DB Change"
                checked={form.db_change}
                onChange={(v) => setForm({ ...form, db_change: v })}
              />
              <Check
                label="PII Impact"
                checked={form.pii_impact}
                onChange={(v) => setForm({ ...form, pii_impact: v })}
              />
            </Grid>
          </div>
          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: 14,
              padding: "10px 18px",
              background: "#276749",
              color: "#fff",
              border: 0,
              borderRadius: 6,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            {loading ? "Processing..." : "Submit Request"}
          </button>
        </Section>
      </form>

      {/* STEP 3 */}
      {result ? (
        <Section title="Step 3 — Policy Gate Decision">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))",
              gap: 10,
              marginBottom: 14,
            }}
          >
            <KPI label="Status" value={result.status} />
            <KPI
              label="Risk"
              value={`${(result.risk_label || "").toUpperCase()} (${result.risk_score})`}
              color={riskColor[result.risk_label] || "#333"}
            />
            <KPI
              label="Required Approver"
              value={result.required_approver || "none"}
            />
          </div>

          {/* Decision summary */}
          {result.decision_summary ? (
            <div
              style={{
                background:
                  result.status === "auto_approved" ? "#f0fff4" : "#fff5f5",
                border: `1px solid ${result.status === "auto_approved" ? "#9ae6b4" : "#fcb"}`,
                borderRadius: 6,
                padding: 12,
                marginBottom: 10,
                fontWeight: 600,
              }}
            >
              {result.decision_summary}
            </div>
          ) : null}

          {/* AI GOVERNANCE RATIONALE — NEW */}
          {result.ai_rationale ? (
            <div
              style={{
                background: "#f0f4ff",
                border: "1px solid #7f9cf5",
                borderRadius: 6,
                padding: 12,
                marginBottom: 10,
              }}
            >
              <b
                style={{ display: "block", marginBottom: 6, color: "#3730a3" }}
              >
                🤖 AI Governance Rationale
              </b>
              <p
                style={{
                  margin: 0,
                  fontSize: 14,
                  lineHeight: 1.7,
                  color: "#1a1a2e",
                }}
              >
                {result.ai_rationale}
              </p>
            </div>
          ) : null}

          {result.escalation_reason ? (
            <p style={{ color: "#c53030", fontWeight: 600 }}>
              {result.escalation_reason}
            </p>
          ) : null}

          {Array.isArray(result.policy_violations) &&
          result.policy_violations.length > 0 ? (
            <div
              style={{
                background: "#fff5f5",
                border: "1px solid #fcb",
                borderRadius: 6,
                padding: 10,
                marginBottom: 10,
              }}
            >
              <b>Policy Violations ({result.policy_violations.length})</b>
              <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                {result.policy_violations.map((x, i) => (
                  <li key={i} style={{ color: "#c53030" }}>
                    {x}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {Array.isArray(result.required_checks) &&
          result.required_checks.length > 0 ? (
            <div
              style={{
                background: "#f0fff4",
                border: "1px solid #9ae6b4",
                borderRadius: 6,
                padding: 10,
                marginBottom: 10,
              }}
            >
              <b>Required Checks</b>
              <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                {result.required_checks.map((x, i) => (
                  <li key={i}>{x}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {result.decision_details?.applicable_policies?.length > 0 ? (
            <div
              style={{
                background: "#fef3c7",
                border: "1px solid #fbbf24",
                borderRadius: 6,
                padding: 10,
                marginBottom: 10,
              }}
            >
              <b>Applicable Policies (RAG Retrieved)</b>
              <ul style={{ margin: "6px 0 0", paddingLeft: 18, fontSize: 13 }}>
                {result.decision_details.applicable_policies.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {Array.isArray(result.audit_log) && result.audit_log.length > 0 ? (
            <div
              style={{
                background: "#ebf8ff",
                border: "1px solid #90cdf4",
                borderRadius: 6,
                padding: 10,
                marginBottom: 10,
              }}
            >
              <b>Audit Log</b>
              <ul style={{ margin: "6px 0 0", paddingLeft: 18, fontSize: 13 }}>
                {result.audit_log.map((x, i) => (
                  <li key={i}>{JSON.stringify(x)}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <pre
            style={{
              background: "#0f172a",
              color: "#dbeafe",
              padding: 10,
              borderRadius: 6,
              overflowX: "auto",
              fontSize: 12,
            }}
          >
            {JSON.stringify(result, null, 2)}
          </pre>
        </Section>
      ) : null}

      {/* STEP 4 */}
      <Section title="Step 4 — Approvals Queue (Release Manager View)">
        <button
          onClick={loadQueue}
          style={{
            padding: "8px 12px",
            marginBottom: 10,
            borderRadius: 6,
            cursor: "pointer",
          }}
        >
          Refresh Queue
        </button>

        {queue.length === 0 ? (
          <p style={{ color: "#555" }}>No pending approvals.</p>
        ) : (
          queue.map((item) => (
            <div
              key={item.approval_id}
              style={{
                border: `2px solid ${riskColor[item.risk_label] || "#ccc"}`,
                borderRadius: 8,
                padding: 12,
                marginBottom: 12,
              }}
            >
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))",
                  gap: 8,
                  marginBottom: 10,
                }}
              >
                <KPI label="Service" value={item.service_name} />
                <KPI label="Type" value={item.change_type} />
                <KPI
                  label="Risk"
                  value={`${(item.risk_label || "").toUpperCase()} (${item.risk_score})`}
                  color={riskColor[item.risk_label]}
                />
                <KPI label="Approver Needed" value={item.required_approver} />
              </div>

              <p style={{ fontSize: 13, color: "#c53030", margin: "0 0 8px" }}>
                {item.escalation_reason}
              </p>

              {/* AI rationale in queue card */}
              {item.ai_rationale ? (
                <div
                  style={{
                    background: "#f0f4ff",
                    border: "1px solid #7f9cf5",
                    borderRadius: 6,
                    padding: 10,
                    marginBottom: 8,
                    fontSize: 13,
                  }}
                >
                  <b style={{ color: "#3730a3" }}>🤖 AI Rationale</b>
                  <p style={{ margin: "4px 0 0", lineHeight: 1.6 }}>
                    {item.ai_rationale}
                  </p>
                </div>
              ) : null}

              {Array.isArray(item.policy_violations) &&
              item.policy_violations.length > 0 ? (
                <div style={{ fontSize: 13, marginBottom: 8 }}>
                  <b>Violations:</b>
                  <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
                    {item.policy_violations.map((v, i) => (
                      <li key={i} style={{ color: "#c53030" }}>
                        {v}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div
                style={{
                  display: "flex",
                  gap: 8,
                  flexWrap: "wrap",
                  marginTop: 10,
                }}
              >
                <select
                  value={decisionForm.decision}
                  onChange={(e) =>
                    setDecisionForm({
                      ...decisionForm,
                      decision: e.target.value,
                    })
                  }
                  style={{ padding: 8, borderRadius: 4 }}
                >
                  <option value="approve">approve</option>
                  <option value="reject">reject</option>
                </select>
                <input
                  placeholder="Approver name"
                  value={decisionForm.approver_name}
                  onChange={(e) =>
                    setDecisionForm({
                      ...decisionForm,
                      approver_name: e.target.value,
                    })
                  }
                  style={{ padding: 8, borderRadius: 4 }}
                />
                <select
                  value={decisionForm.approver_role}
                  onChange={(e) =>
                    setDecisionForm({
                      ...decisionForm,
                      approver_role: e.target.value,
                    })
                  }
                  style={{ padding: 8, borderRadius: 4 }}
                >
                  <option value="release_manager">release_manager</option>
                  <option value="security_reviewer">security_reviewer</option>
                  <option value="compliance_reviewer">
                    compliance_reviewer
                  </option>
                </select>
                <input
                  placeholder="Comment (optional)"
                  value={decisionForm.comment}
                  onChange={(e) =>
                    setDecisionForm({
                      ...decisionForm,
                      comment: e.target.value,
                    })
                  }
                  style={{ padding: 8, borderRadius: 4, minWidth: 200 }}
                />
                <button
                  onClick={() => submitDecision(item.approval_id)}
                  style={{
                    padding: "8px 14px",
                    background: "#2b6cb0",
                    color: "#fff",
                    border: 0,
                    borderRadius: 6,
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  Submit Decision
                </button>
              </div>
            </div>
          ))
        )}
      </Section>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div
      style={{
        border: "1px solid #ddd",
        borderRadius: 8,
        padding: 14,
        marginBottom: 14,
      }}
    >
      <h3
        style={{
          margin: "0 0 12px",
          borderBottom: "1px solid #eee",
          paddingBottom: 8,
        }}
      >
        {title}
      </h3>
      {children}
    </div>
  );
}

function KPI({ label, value, color }) {
  return (
    <div
      style={{
        background: "#f9fafb",
        border: "1px solid #e2e8f0",
        borderRadius: 8,
        padding: 10,
      }}
    >
      <div style={{ fontSize: 12, color: "#666", marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontWeight: 700, color: color || "#11212d" }}>{value}</div>
    </div>
  );
}

function Grid({ children }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))",
        gap: 10,
      }}
    >
      {children}
    </div>
  );
}

function Input({ label, value, onChange }) {
  return (
    <label style={{ display: "block" }}>
      <div style={{ fontSize: 13, marginBottom: 4 }}>{label}</div>
      <input
        style={{
          width: "100%",
          padding: 8,
          borderRadius: 4,
          border: "1px solid #ccc",
        }}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

function Select({ label, value, onChange, options }) {
  return (
    <label style={{ display: "block" }}>
      <div style={{ fontSize: 13, marginBottom: 4 }}>{label}</div>
      <select
        style={{
          width: "100%",
          padding: 8,
          borderRadius: 4,
          border: "1px solid #ccc",
        }}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((x) => (
          <option key={x} value={x}>
            {x}
          </option>
        ))}
      </select>
    </label>
  );
}

function Check({ label, checked, onChange }) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      {label}
    </label>
  );
}
