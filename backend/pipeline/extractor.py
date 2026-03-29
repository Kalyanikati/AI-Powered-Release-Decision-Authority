import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


SYSTEM_PROMPT = """
You are an enterprise decision extraction engine.

Input may be English, Hindi, or code-mixed Hinglish.
Preserve original quote language exactly. Do not translate quotes.

Return ONLY valid JSON with this shape:
{
  "decisions": [
    {
      "decision": "string",
      "owner": "string or null",
      "deadline": "string or null",
      "quote": "exact quote"
    }
  ],
  "ambiguities": [
    {
      "phrase": "string",
      "quote": "exact quote"
    }
  ],
  "conflicts": [
    {
      "statement1": "string",
      "statement2": "string",
      "reason": "owner conflict | deadline conflict | intent conflict"
    }
  ]
}
""".strip()


def analyze_with_llm(transcript: str) -> Dict[str, List[Dict[str, Any]]]:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY missing in backend/.env")

    client = Groq(api_key=GROQ_API_KEY)

    attempt_1 = _call_model(client, transcript)
    parsed_1 = _parse_json_safely(attempt_1)

    if _valid_shape(parsed_1):
        return _normalize(parsed_1)

    # one repair attempt
    repair_prompt = (
        "Your previous output was invalid. Return only strict JSON with keys "
        "decisions, ambiguities, conflicts. No markdown.\n\nTranscript:\n"
        + transcript
    )
    attempt_2 = _call_model(client, repair_prompt, use_system=True)
    parsed_2 = _parse_json_safely(attempt_2)

    if _valid_shape(parsed_2):
        return _normalize(parsed_2)

    return {"decisions": [], "ambiguities": [], "conflicts": []}


def _call_model(client: Groq, user_content: str, use_system: bool = True) -> str:
    messages = []
    if use_system:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    messages.append({"role": "user", "content": f"Transcript:\n{user_content}"})

    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0,
        messages=messages,
    )
    return resp.choices[0].message.content or ""


def _parse_json_safely(raw: str) -> Dict[str, Any]:
    text = raw.strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    try:
        return json.loads(text)
    except Exception:
        return {}


def _valid_shape(obj: Dict[str, Any]) -> bool:
    if not isinstance(obj, dict):
        return False
    for k in ["decisions", "ambiguities", "conflicts"]:
        if k not in obj or not isinstance(obj[k], list):
            return False
    return True


def _normalize(obj: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    decisions = []
    for d in obj.get("decisions", []):
        if not isinstance(d, dict):
            continue
        decisions.append(
            {
                "decision": d.get("decision"),
                "owner": d.get("owner"),
                "deadline": d.get("deadline"),
                "quote": d.get("quote"),
            }
        )

    ambiguities = []
    for a in obj.get("ambiguities", []):
        if not isinstance(a, dict):
            continue
        ambiguities.append(
            {
                "phrase": a.get("phrase"),
                "quote": a.get("quote"),
            }
        )

    conflicts = []
    for c in obj.get("conflicts", []):
        if not isinstance(c, dict):
            continue
        conflicts.append(
            {
                "statement1": c.get("statement1"),
                "statement2": c.get("statement2"),
                "reason": c.get("reason"),
            }
        )

    return {
        "decisions": decisions,
        "ambiguities": ambiguities,
        "conflicts": conflicts,
    }