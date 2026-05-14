from __future__ import annotations

from pydantic import BaseModel, Field


class Source(BaseModel):
    document_id: str
    filename: str
    page_number: int | None = None
    chunk_text_preview: str
    score: float


class CitationValidation(BaseModel):
    status: str
    coverage_score: float
    cited_sources: int
    supporting_sources: list[str]
    warnings: list[str]


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    session_id: str | None = None
    document_ids: list[str] | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    stream: bool = False


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    citation_validation: CitationValidation | None = None
    session_id: str | None = None
    latency_ms: int


class SessionCreateRequest(BaseModel):
    metadata: dict | None = None


class SessionCreateResponse(BaseModel):
    session_id: str
    created_at: str
    expires_at: str | None = None
