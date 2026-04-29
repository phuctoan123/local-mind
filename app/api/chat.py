from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import settings
from app.database import get_connection
from app.db.repositories.document_repo import DocumentRepo
from app.db.repositories.session_repo import SessionRepo
from app.dependencies import get_llm_client, get_retrieval_engine
from app.models.chat import ChatRequest, ChatResponse, SessionCreateRequest, SessionCreateResponse
from app.services.llm_client import LLMUnavailableError
from app.services.rag_service import RagService
from app.services.embedding_service import EmbeddingServiceUnavailableError

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    with get_connection() as conn:
        doc_repo = DocumentRepo(conn)
        if doc_repo.count_ready() == 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "no_documents",
                    "message": "No documents with status READY found.",
                },
            )
        session_repo = SessionRepo(conn)
        if request.session_id and not session_repo.exists(request.session_id):
            raise HTTPException(
                status_code=404,
                detail={"error": "session_not_found", "message": "Session does not exist."},
            )
        service = RagService(get_retrieval_engine(), get_llm_client(), session_repo)
        if request.stream:
            return StreamingResponse(
                _sse_chat(RagService(get_retrieval_engine(), get_llm_client()), request),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        try:
            return await service.chat(request)
        except EmbeddingServiceUnavailableError as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "embedding_unavailable",
                    "message": f"{_provider_label(settings.embedding_provider)} embedding request failed: {exc}",
                },
            ) from exc
        except LLMUnavailableError as exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "llm_unavailable",
                    "message": f"{_provider_label(settings.llm_provider)} chat request failed: {exc}",
                },
            ) from exc


async def _sse_chat(service: RagService, request: ChatRequest):
    try:
        async for event in service.stream_chat_events(request):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    except EmbeddingServiceUnavailableError as exc:
        event = {
            "type": "error",
            "error": "embedding_unavailable",
            "message": f"{_provider_label(settings.embedding_provider)} embedding request failed: {exc}",
        }
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    except LLMUnavailableError as exc:
        event = {
            "type": "error",
            "error": "llm_unavailable",
            "message": f"{_provider_label(settings.llm_provider)} chat request failed: {exc}",
        }
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def _provider_label(provider: str) -> str:
    labels = {"google": "Google AI Studio", "mistral": "Mistral/LeChat"}
    return labels.get(provider.lower(), "Ollama")


@router.post("/sessions", response_model=SessionCreateResponse, status_code=201)
def create_session(request: SessionCreateRequest | None = None):
    with get_connection() as conn:
        session = SessionRepo(conn).create((request.metadata if request else None) or {})
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.session_ttl_minutes)
    return SessionCreateResponse(
        session_id=session["id"],
        created_at=session["created_at"],
        expires_at=expires_at.isoformat(),
    )


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str):
    with get_connection() as conn:
        repo = SessionRepo(conn)
        if not repo.exists(session_id):
            raise HTTPException(
                status_code=404,
                detail={"error": "session_not_found", "message": "Session does not exist."},
            )
        repo.delete(session_id)
    return None
