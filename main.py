"""The HTTP surface.

Two endpoints, both of which run the same pipeline: retrieve, generate, check.
A deck that fails its checks comes back with status "rejected" and the reasons,
never silently cleaned up - the caller has to see why.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from pydantic import BaseModel, Field

import bedrock
import guardrails
import rag

app = FastAPI(
    title="Oso Cloud",
    description="A curriculum engine for Lugha. Builds flashcard decks from "
                "language-teaching reference material, with citations.",
    version="0.1.0",
)

_index: dict | None = None


def index() -> dict:
    """Loaded once, lazily - so importing the app never needs an index on disk."""
    global _index
    if _index is None:
        _index = rag.load_index()
    return _index


class LessonRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    k: int = Field(rag.TOP_K, ge=1, le=12)


class DeckRequest(BaseModel):
    language: str = Field(..., min_length=1, max_length=40, examples=["Spanish"])
    code: str = Field(..., min_length=2, max_length=3, examples=["es"])
    stage: str = Field(..., examples=["survival"])
    level: str = Field(..., examples=["A1"])
    k: int = Field(rag.TOP_K, ge=1, le=12)


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "mock": rag.mock_mode(),
        "model": bedrock.MODEL_ID or None,
        "embed_model": None if rag.mock_mode() else rag.EMBED_MODEL_ID,
        "min_score": rag.min_score(),
    }


@app.post("/lesson")
def lesson(req: LessonRequest) -> dict:
    """Answer a question about teaching a language, grounded in the corpus."""
    hits = rag.search(req.question, k=req.k, index=index())
    result = bedrock.answer(req.question, hits)
    report = guardrails.check_answer(result)
    return {
        "question": req.question,
        **result,
        "retrieved": [{"doc_id": h.doc_id, "heading": h.heading,
                       "score": h.score} for h in hits],
        "checks": {"ok": report.ok, "errors": report.errors,
                   "warnings": report.warnings},
    }


@app.post("/deck")
def deck(req: DeckRequest) -> dict:
    """Build one deck and report whether it may ship."""
    query = (f"{req.level} {req.language} {req.stage} stage: which words and "
             f"phrases to teach, and the deck format")
    hits = rag.search(query, k=req.k, index=index())

    if not hits:
        return {
            "status": "rejected",
            "deck": None,
            "checks": {"ok": False,
                       "errors": ["nothing retrieved above the score floor"],
                       "warnings": []},
            "retrieved": [],
        }

    candidate = bedrock.generate_deck(
        req.language, req.code, req.stage, req.level, hits)
    report = guardrails.check_deck(candidate, req.code, req.stage, req.level)

    return {
        "status": "accepted" if report.ok else "rejected",
        "deck": candidate,
        "checks": {"ok": report.ok, "errors": report.errors,
                   "warnings": report.warnings},
        "retrieved": [{"doc_id": h.doc_id, "heading": h.heading,
                       "score": h.score} for h in hits],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
