from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.config import get_active_llm_model
from app.database import get_connection
from app.db.repositories.session_repo import SessionRepo
from app.dependencies import get_llm_client, get_retrieval_engine
from app.models.chat import ChatRequest
from app.models.openai import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    OpenAIMessage,
)
from app.services.embedding_service import EmbeddingServiceUnavailableError
from app.services.llm_client import LLMUnavailableError
from app.services.rag_service import RagService

router = APIRouter(tags=["openai-compatible"])


@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    chat_request = ChatRequest(
        query=request.latest_user_message,
        document_ids=request.document_ids,
        top_k=request.top_k,
        stream=request.stream,
    )
    with get_connection() as conn:
        service = RagService(get_retrieval_engine(), get_llm_client(), SessionRepo(conn))
        if request.stream:
            return StreamingResponse(
                _openai_sse(
                    RagService(get_retrieval_engine(), get_llm_client()),
                    chat_request,
                    request.model or get_active_llm_model(),
                ),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        try:
            response = await service.chat(chat_request)
        except (EmbeddingServiceUnavailableError, LLMUnavailableError) as exc:
            raise HTTPException(
                status_code=503,
                detail={"error": "provider_unavailable", "message": str(exc)},
            ) from exc

    return ChatCompletionResponse(
        model=request.model or get_active_llm_model(),
        choices=[
            ChatCompletionChoice(
                message=OpenAIMessage(role="assistant", content=response.answer),
            )
        ],
    )


async def _openai_sse(service: RagService, request: ChatRequest, model: str):
    try:
        async for event in service.stream_chat_events(request):
            if event["type"] == "token":
                payload = {
                    "object": "chat.completion.chunk",
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": event["content"]},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            elif event["type"] == "done":
                payload = {
                    "object": "chat.completion.chunk",
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
    except (EmbeddingServiceUnavailableError, LLMUnavailableError) as exc:
        payload = {"error": {"message": str(exc), "type": "provider_error"}}
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
