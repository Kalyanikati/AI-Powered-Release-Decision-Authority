import json
import os
from typing import Any, Dict

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """
You are an enterprise meeting decision analyzer.

Handle English, Hindi, and code-mixed Hinglish.
Preserve quote text in original language. Do not translate quotes.

Return ONLY valid JSON with this exact shape:
{
  "decisions": [
    {
      "decision": "string",
      "owner": "string or null",
      "deadline": "string or null",
      "quote": "exact supporting quote"
    }
  ],
  "ambiguities": [
    {
      "phrase": "ambiguous phrase",
      "quote": "exact supporting quote"
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

If there is no item for a section, return an empty array for that section.
No markdown, no explanation.
""".strip()


def analyze_with_llm(transcript: str) -> Dict[str, Any]:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing in backend/.env")

    client = Groq(api_key=GROQ_API_KEY)

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Transcript:\n{transcript}"},
        ],
    )

    raw = response.choices[0].message.content or ""
    parsed = _safe_json_load(raw)

    decisions = parsed.get("decisions", [])
    ambiguities = parsed.get("ambiguities", [])
    conflicts = parsed.get("conflicts", [])

    if not isinstance(decisions, list):
        decisions = []
    if not isinstance(ambiguities, list):
        ambiguities = []
    if not isinstance(conflicts, list):
        conflicts = []

    return {
        "decisions": decisions,
        "ambiguities": ambiguities,
        "conflicts": conflicts,
    }


def _safe_json_load(raw: str) -> Dict[str, Any]:
    text = raw.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    return json.loads(text)