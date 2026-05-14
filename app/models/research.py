from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.chat import CitationValidation, Source


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    document_ids: list[str] | None = None
    max_steps: int = Field(default=3, ge=1, le=5)
    top_k_per_step: int = Field(default=4, ge=1, le=10)


class ResearchStep(BaseModel):
    step: int
    query: str
    sources: list[Source]


class ResearchResponse(BaseModel):
    answer: str
    steps: list[ResearchStep]
    sources: list[Source]
    citation_validation: CitationValidation | None = None
    latency_ms: int
