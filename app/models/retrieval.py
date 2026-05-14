from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.chat import Source


class ChunkSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    document_ids: list[str] | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)


class RetrievedSource(Source):
    chunk_index: int
    text: str


class ChunkSearchResponse(BaseModel):
    object: str = "list"
    model: str = "localmind"
    data: list[RetrievedSource]


class RetrievalDebugRequest(ChunkSearchRequest):
    pass


class RankedRetrievedSource(RetrievedSource):
    rank: int


class RetrievalDebugResponse(BaseModel):
    object: str = "retrieval_debug"
    model: str = "localmind"
    original_query: str
    effective_query: str
    query_was_rewritten: bool
    mode: str
    vector: list[RankedRetrievedSource]
    bm25: list[RankedRetrievedSource]
    fused: list[RankedRetrievedSource]
    reranked: list[RankedRetrievedSource]
    fallback: list[RankedRetrievedSource]
    data: list[RankedRetrievedSource]
