import os
from typing import List

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

RATIONALE_PROMPT = """
You are an SDLC governance AI assistant.

A developer has submitted a software release request. Based on the information below, write a clear, 
concise 3-5 sentence explanation of the governance decision — why this release is safe or risky, 
what specific policies apply, and what the approver should focus on.

Write in plain English. Be specific. Do not repeat the field values back verbatim.

Release context:
- Service: {service_name}
- Environment: {environment}
- Change type: {change_type}
- Urgency: {urgency}
- Risk score: {risk_score}/100 ({risk_label} risk)
- Policy violations: {violations_text}
- Test evidence: {has_test_evidence}
- Security scan: {has_security_scan}
- Rollback plan: {has_rollback_plan}
- DB change: {db_change}
- PII impact: {pii_impact}

Relevant SDLC policies retrieved:
{policies_text}

Write the governance rationale now:
""".strip()


def generate_ai_rationale(
    service_name: str,
    environment: str,
    change_type: str,
    urgency: str,
    risk_score: int,
    risk_label: str,
    policy_violations: List[str],
    retrieved_policies: List[str],
    has_test_evidence: bool,
    has_security_scan: bool,
    has_rollback_plan: bool,
    db_change: bool,
    pii_impact: bool,
) -> str:
    violations_text = (
        "\n".join(f"- {v}" for v in policy_violations)
        if policy_violations
        else "None"
    )
    policies_text = (
        "\n".join(f"- {p}" for p in retrieved_policies)
        if retrieved_policies
        else "No specific policies retrieved."
    )

    prompt = RATIONALE_PROMPT.format(
        service_name=service_name,
        environment=environment,
        change_type=change_type,
        urgency=urgency,
        risk_score=risk_score,
        risk_label=risk_label,
        violations_text=violations_text,
        has_test_evidence=has_test_evidence,
        has_security_scan=has_security_scan,
        has_rollback_plan=has_rollback_plan,
        db_change=db_change,
        pii_impact=pii_impact,
        policies_text=policies_text,
    )

    if not GROQ_API_KEY:
        return _fallback_rationale(risk_label, policy_violations, environment)

    try:
        from groq import Groq

        client = Groq(api_key=GROQ_API_KEY)
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": "You are an SDLC governance expert. Write concise, actionable rationale.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        print("AI rationale generation failed, using fallback:", exc)
        return _fallback_rationale(risk_label, policy_violations, environment)


def _fallback_rationale(
    risk_label: str, policy_violations: List[str], environment: str
) -> str:
    if not policy_violations and environment != "production":
        return (
            f"This release has been assessed as {risk_label} risk. "
            "All required governance checks have passed and no policy violations were detected. "
            "The release may proceed without human intervention."
        )
    return (
        f"This release has been assessed as {risk_label} risk with "
        f"{len(policy_violations)} policy violation(s) detected. "
        "The release requires human review before proceeding. "
        "Please review the listed violations and applicable policies before approving."
    )