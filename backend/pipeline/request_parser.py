import json
import os
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

PARSE_PROMPT = """
You are a release request parser for enterprise SDLC governance.

Extract fields from the raw release request text below and return ONLY valid JSON.

Required JSON shape:
{
  "requester_name": "string or null",
  "requester_role": "developer|tech_lead",
  "service_name": "string or null",
  "environment": "staging|production",
  "change_type": "release|hotfix",
  "urgency": "normal|high|critical",
  "planned_window": "string or null",
  "has_test_evidence": true|false,
  "has_security_scan": true|false,
  "has_rollback_plan": true|false,
  "db_change": true|false,
  "pii_impact": true|false,
  "notes": "short description of change",
  "pr_links": ["string"],
  "jira_links": ["string"],
  "monitoring_tools": ["string"],
  "raw_approver_mention": "string or null"
}

Rules:
- If test coverage is mentioned, has_test_evidence is true.
- If rollback process is mentioned, has_rollback_plan is true.
- If security/compliance scan is not explicitly mentioned, has_security_scan is false.
- If DB or data changes are mentioned, db_change is true.
- If PII, user data, or sensitive fields are mentioned, pii_impact is true.
- Change type is hotfix if patch/fix is implied, else release.
- Environment is production if prod or live is implied.
- Return JSON only, no markdown.

Raw request:
{raw_text}
""".strip()


def parse_raw_request(raw_text: str) -> Dict[str, Any]:
    if not GROQ_API_KEY:
        return _fallback_parse(raw_text)

    try:
        from groq import Groq

        client = Groq(api_key=GROQ_API_KEY)
        prompt = PARSE_PROMPT.replace("{raw_text}", raw_text)

        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
        )
        raw = resp.choices[0].message.content or ""
        text = raw.strip()
        if text.startswith("```"):
            text = text.replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            text = text[start: end + 1]
        return json.loads(text)
    except Exception as exc:
        print("LLM parse failed, using fallback:", exc)
        return _fallback_parse(raw_text)


def _fallback_parse(text: str) -> Dict[str, Any]:
    lower = text.lower()
    return {
        "requester_name": None,
        "requester_role": "developer",
        "service_name": None,
        "environment": "production" if "prod" in lower else "staging",
        "change_type": "hotfix" if any(w in lower for w in ["hotfix", "fix", "patch"]) else "release",
        "urgency": "high" if any(w in lower for w in ["urgent", "critical", "asap"]) else "normal",
        "planned_window": None,
        "has_test_evidence": any(w in lower for w in ["unit test", "test coverage", "qa"]),
        "has_security_scan": any(w in lower for w in ["security scan", "vulnerability scan"]),
        "has_rollback_plan": any(w in lower for w in ["rollback", "revert", "dop"]),
        "db_change": any(w in lower for w in ["db", "database", "migration", "schema"]),
        "pii_impact": any(w in lower for w in ["pii", "user data", "personal", "sensitive"]),
        "notes": text[:200],
        "pr_links": [],
        "jira_links": [],
        "monitoring_tools": [],
        "raw_approver_mention": None,
    }