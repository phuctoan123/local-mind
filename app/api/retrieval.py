from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.dependencies import get_retrieval_engine
from app.models.retrieval import (
    ChunkSearchRequest,
    ChunkSearchResponse,
    RankedRetrievedSource,
    RetrievalDebugRequest,
    RetrievalDebugResponse,
    RetrievedSource,
)
from app.services.embedding_service import EmbeddingServiceUnavailableError
from app.services.vector_store import RetrievedChunk

router = APIRouter(tags=["retrieval"])


@router.post("/chunks", response_model=ChunkSearchResponse)
async def retrieve_chunks(request: ChunkSearchRequest):
    try:
        chunks = await get_retrieval_engine().retrieve(
            request.query,
            top_k=request.top_k,
            document_ids=request.document_ids,
            min_score=request.min_score,
        )
    except EmbeddingServiceUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "embedding_unavailable",
                "message": f"{settings.embedding_provider} embedding request failed: {exc}",
            },
        ) from exc

    return ChunkSearchResponse(
        data=[
            RetrievedSource(
                document_id=chunk.document_id,
                filename=chunk.filename,
                page_number=chunk.page_number,
                chunk_text_preview=chunk.text[:200],
                score=round(chunk.score, 4),
                chunk_index=chunk.chunk_index,
                text=chunk.text,
            )
            for chunk in chunks
        ]
    )


@router.post("/chunks/debug", response_model=RetrievalDebugResponse)
async def debug_retrieve_chunks(request: RetrievalDebugRequest):
    try:
        trace = await get_retrieval_engine().retrieve_debug(
            request.query,
            top_k=request.top_k,
            document_ids=request.document_ids,
            min_score=request.min_score,
        )
    except EmbeddingServiceUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "embedding_unavailable",
                "message": f"{settings.embedding_provider} embedding request failed: {exc}",
            },
        ) from exc

    return RetrievalDebugResponse(
        original_query=trace.original_query,
        effective_query=trace.effective_query,
        query_was_rewritten=trace.query_was_rewritten,
        mode=trace.mode,
        vector=_ranked_sources(trace.vector_chunks),
        bm25=_ranked_sources(trace.bm25_chunks),
        fused=_ranked_sources(trace.fused_chunks),
        reranked=_ranked_sources(trace.reranked_chunks),
        fallback=_ranked_sources(trace.fallback_chunks),
        data=_ranked_sources(trace.returned_chunks),
    )


def _ranked_sources(chunks: list[RetrievedChunk]) -> list[RankedRetrievedSource]:
    return [
        RankedRetrievedSource(
            rank=index,
            document_id=chunk.document_id,
            filename=chunk.filename,
            page_number=chunk.page_number,
            chunk_text_preview=chunk.text[:200],
            score=round(chunk.score, 4),
            chunk_index=chunk.chunk_index,
            text=chunk.text,
        )
        for index, chunk in enumerate(chunks, start=1)
    ]
