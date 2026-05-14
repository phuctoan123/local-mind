from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.database import get_connection
from app.db.repositories.document_repo import DocumentRepo
from app.dependencies import get_llm_client, get_retrieval_engine
from app.models.research import ResearchRequest, ResearchResponse
from app.services.embedding_service import EmbeddingServiceUnavailableError
from app.services.llm_client import LLMUnavailableError
from app.services.research_service import ResearchService

router = APIRouter(tags=["research"])


@router.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest):
    with get_connection() as conn:
        if DocumentRepo(conn).count_ready() == 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "no_documents",
                    "message": "No documents with status READY found.",
                },
            )

    service = ResearchService(get_retrieval_engine(), get_llm_client())
    try:
        return await service.research(request)
    except EmbeddingServiceUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "embedding_unavailable",
                "message": f"{settings.embedding_provider} embedding request failed: {exc}",
            },
        ) from exc
    except LLMUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "llm_unavailable",
                "message": f"{settings.llm_provider} chat request failed: {exc}",
            },
        ) from exc
