# Multilingual Decision Integrity Engine

GenAI-powered system to detect ambiguity, conflict, and execution risk in enterprise meeting decisions.

Built for ET Gen AI Hackathon Phase 2.

## Problem Statement

Enterprises run thousands of meetings where decisions are made, but execution often fails due to:
- unclear ownership
- vague deadlines
- ambiguous commitments
- contradictory statements

Most existing tools provide transcription and summarization, but they do not measure structural decision clarity.

## Solution Overview

This project converts raw meeting transcripts into structured decision intelligence.

Core capabilities:
- transcript parsing with speaker-aware preprocessing
- LLM-based decision extraction with quote grounding
- ambiguity detection in English, Hindi, and code-mixed text
- conflict detection across owners, deadlines, and intent
- deterministic Decision Integrity Score from 0 to 100 with explainable breakdown

## Architecture

Pipeline:
1. Parser
2. LLM Extractor
3. Ambiguity Detector
4. Conflict Detector
5. Scoring Engine
6. Frontend Visualization

## Tech Stack

Frontend:
- React
- Vite
- CSS

Backend:
- FastAPI
- Groq API
- python-dotenv
- langdetect

## Repository Structure

- frontend
- backend
- backend/main.py
- backend/pipeline/parser.py
- backend/pipeline/extractor.py
- backend/pipeline/ambiguity.py
- backend/pipeline/conflict.py
- backend/pipeline/scorer.py
- backend/lexicons/uncertainty_en.txt
- backend/lexicons/uncertainty_hi.txt

## Setup Instructions

Prerequisites:
- Node.js 18+
- Python 3.9+
- Groq API key

Backend:
1. cd backend
2. python3 -m venv venv
3. source venv/bin/activate
4. pip install -r requirements.txt
5. create .env file with:
   GROQ_API_KEY=your_key_here
   GROQ_MODEL=llama-3.3-70b-versatile
6. run:
   uvicorn main:app --reload --port 8000

Frontend:
1. cd frontend
2. npm install
3. npm run dev

Default URLs:
- Frontend: http://localhost:5173
- Backend: http://127.0.0.1:8000

## API Contract

Endpoint:
POST /analyze

Request:
{
  "text": "Speaker 1: ... Speaker 2: ..."
}

Response:
{
  "decisions": [],
  "ambiguities": [],
  "conflicts": [],
  "score": 84,
  "label": "Low Risk",
  "breakdown": {}
}

## Scoring Logic

Score starts at 100 and reduces by deterministic penalties:
- missing owner
- missing deadline
- ambiguity markers
- detected conflicts

Output includes:
- final score
- risk label
- penalty breakdown

## Multilingual Support

Supports:
- English
- Hindi
- code-mixed enterprise conversations

Design principle:
- preserve original quote language
- evaluate execution clarity, not business correctness

## Example Output Signals

- decisions extracted with owner and deadline
- ambiguity phrases with supporting quotes
- contradiction pairs with conflict reason
- final integrity score with explainability

## Evaluation Metrics

- extraction quality
- ambiguity precision and recall
- conflict detection F1
- false positive rate
- quote-grounding coverage

## Current Limitations

- hackathon prototype scope
- no live Zoom/Teams streaming integration yet
- no enterprise auth and role management yet

## Future Roadmap

- real-time meeting analysis
- native Zoom and Teams connectors
- Slack and email decision intelligence
- domain-specific feasibility plug-ins

## One-line Positioning

We do not judge whether a decision is correct; we judge whether it is clear enough to execute.
