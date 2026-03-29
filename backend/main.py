from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline.parser import parse_transcript
from pipeline.extractor import analyze_with_llm
from pipeline.ambiguity import detect_ambiguity
from pipeline.conflict import detect_conflicts
from pipeline.scorer import compute_score


app = FastAPI(title="Multilingual Decision Integrity Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hackathon mode
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TranscriptRequest(BaseModel):
    text: str


@app.get("/")
def root() -> Dict[str, str]:
    return {"message": "Backend is running"}


@app.post("/analyze")
def analyze(req: TranscriptRequest) -> Dict[str, Any]:
    try:
        utterances = parse_transcript(req.text)
        transcript_for_llm = "\n".join(
            f"{u['speaker']}: {u['text']}" for u in utterances
        )

        llm_out = analyze_with_llm(transcript_for_llm)

        decisions: List[Dict[str, Any]] = llm_out.get("decisions", [])
        llm_ambiguities: List[Dict[str, Any]] = llm_out.get("ambiguities", [])
        llm_conflicts: List[Dict[str, Any]] = llm_out.get("conflicts", [])

        project_root = str(Path(__file__).resolve().parent)
        rule_ambiguities = detect_ambiguity(decisions, project_root)
        rule_conflicts = detect_conflicts(decisions)

        ambiguities = dedupe_dicts(llm_ambiguities + rule_ambiguities)
        conflicts = dedupe_dicts(llm_conflicts + rule_conflicts)

        score_obj = compute_score(decisions, ambiguities, conflicts)

        language_summary = summarize_languages(utterances)

        return {
            "decisions": decisions,
            "ambiguities": ambiguities,
            "conflicts": conflicts,
            "score": score_obj["score"],
            "label": score_obj["label"],
            "breakdown": score_obj["breakdown"],
            "language_summary": language_summary,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def dedupe_dicts(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for item in items:
        key = str(sorted(item.items()))
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def summarize_languages(utterances: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for u in utterances:
        lang = u.get("language_hint", "unknown")
        counts[lang] = counts.get(lang, 0) + 1
    return counts