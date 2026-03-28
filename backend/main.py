from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# ✅ FIX FOR YOUR ERROR (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for hackathon (later restrict)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TranscriptRequest(BaseModel):
    text: str

@app.get("/")
def root():
    return {"message": "Backend is running"}

@app.post("/analyze")
def analyze(req: TranscriptRequest):
    text = req.text

    # Dummy response (replace later with LLM)
    return {
        "decisions": [
            {
                "decision": "Finalize deployment",
                "owner": "Rahul",
                "deadline": "March 30",
                "quote": "Rahul will finalize deployment by March 30"
            }
        ],
        "ambiguity": [
            {"phrase": "maybe", "quote": "Maybe Priya owns QA"}
        ],
        "conflicts": [
            {
                "statement1": "Priya owns QA",
                "statement2": "QA owner is Amit",
                "reason": "owner conflict"
            }
        ],
        "score": 60,
        "breakdown": {
            "owner_penalty": 0,
            "deadline_penalty": 0,
            "ambiguity_penalty": 15,
            "conflict_penalty": 25
        }
    }