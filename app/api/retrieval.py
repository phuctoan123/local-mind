from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.dependencies import get_retrieval_engine
from app.models.retrieval import ChunkSearchRequest, ChunkSearchResponse, RetrievedSource
from app.services.embedding_service import EmbeddingServiceUnavailableError

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
