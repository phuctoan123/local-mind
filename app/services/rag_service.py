from __future__ import annotations

from collections.abc import AsyncIterator
import time

from app.config import settings
from app.db.repositories.session_repo import SessionRepo
from app.ingestion.chunker import estimate_tokens
from app.models.chat import ChatRequest, ChatResponse, Source
from app.services.llm_client import OllamaClient
from app.services.retrieval_engine import RetrievalEngine
from app.services.vector_store import RetrievedChunk


class RagService:
    def __init__(
        self,
        retrieval_engine: RetrievalEngine,
        llm_client: OllamaClient,
        session_repo: SessionRepo | None = None,
    ):
        self.retrieval_engine = retrieval_engine
        self.llm_client = llm_client
        self.session_repo = session_repo

    async def chat(self, request: ChatRequest) -> ChatResponse:
        started = time.perf_counter()
        chunks = await self.retrieval_engine.retrieve(
            request.query,
            top_k=request.top_k,
            document_ids=request.document_ids,
            min_score=settings.min_similarity_score,
        )
        low_confidence = False
        if not chunks and settings.min_similarity_score > 0:
            chunks = await self.retrieval_engine.retrieve(
                request.query,
                top_k=request.top_k,
                document_ids=request.document_ids,
                min_score=0.0,
            )
            low_confidence = bool(chunks)
        if not chunks:
            answer = "I could not find relevant information in the provided documents."
            return ChatResponse(
                answer=answer,
                sources=[],
                session_id=request.session_id,
                latency_ms=_latency_ms(started),
            )

        history = ""
        if request.session_id and self.session_repo and self.session_repo.exists(request.session_id):
            history = _format_history(
                self.session_repo.history(request.session_id, settings.max_history_turns)
            )
            self.session_repo.add_message(request.session_id, "user", request.query)

        prompt = build_prompt(
            request.query,
            chunks,
            history,
            settings.max_context_tokens,
            low_confidence=low_confidence,
        )
        answer = await self.llm_client.generate(
            prompt,
            stream=False,
            temperature=settings.llm_temperature,
            top_p=settings.llm_top_p,
            num_ctx=settings.llm_num_ctx,
            num_predict=settings.llm_num_predict,
        )
        sources = [
            Source(
                document_id=chunk.document_id,
                filename=chunk.filename,
                page_number=chunk.page_number,
                chunk_text_preview=chunk.text[:200],
                score=round(chunk.score, 4),
            )
            for chunk in chunks
        ]
        if request.session_id and self.session_repo and self.session_repo.exists(request.session_id):
            self.session_repo.add_message(
                request.session_id,
                "assistant",
                str(answer),
                [source.model_dump() for source in sources],
            )
        return ChatResponse(
            answer=str(answer),
            sources=sources,
            session_id=request.session_id,
            latency_ms=_latency_ms(started),
        )

    async def stream_chat_events(self, request: ChatRequest) -> AsyncIterator[dict]:
        started = time.perf_counter()
        chunks = await self.retrieval_engine.retrieve(
            request.query,
            top_k=request.top_k,
            document_ids=request.document_ids,
            min_score=settings.min_similarity_score,
        )
        low_confidence = False
        if not chunks and settings.min_similarity_score > 0:
            chunks = await self.retrieval_engine.retrieve(
                request.query,
                top_k=request.top_k,
                document_ids=request.document_ids,
                min_score=0.0,
            )
            low_confidence = bool(chunks)

        sources = [
            Source(
                document_id=chunk.document_id,
                filename=chunk.filename,
                page_number=chunk.page_number,
                chunk_text_preview=chunk.text[:200],
                score=round(chunk.score, 4),
            )
            for chunk in chunks
        ]
        yield {"type": "sources", "sources": [source.model_dump() for source in sources]}

        if not chunks:
            answer = "I could not find relevant information in the provided documents."
            yield {"type": "token", "content": answer}
            yield {"type": "done", "latency_ms": _latency_ms(started)}
            return

        history = ""
        if request.session_id and self.session_repo and self.session_repo.exists(request.session_id):
            history = _format_history(
                self.session_repo.history(request.session_id, settings.max_history_turns)
            )
            self.session_repo.add_message(request.session_id, "user", request.query)

        prompt = build_prompt(
            request.query,
            chunks,
            history,
            settings.max_context_tokens,
            low_confidence=low_confidence,
        )
        stream = await self.llm_client.generate(
            prompt,
            stream=True,
            temperature=settings.llm_temperature,
            top_p=settings.llm_top_p,
            num_ctx=settings.llm_num_ctx,
            num_predict=settings.llm_num_predict,
        )
        answer_parts: list[str] = []
        async for token in stream:
            answer_parts.append(token)
            yield {"type": "token", "content": token}

        answer = "".join(answer_parts)
        if request.session_id and self.session_repo and self.session_repo.exists(request.session_id):
            self.session_repo.add_message(
                request.session_id,
                "assistant",
                answer,
                [source.model_dump() for source in sources],
            )
        yield {"type": "done", "latency_ms": _latency_ms(started)}


def build_prompt(
    query: str,
    chunks: list[RetrievedChunk],
    history: str = "",
    max_context_tokens: int = 3000,
    low_confidence: bool = False,
) -> str:
    context_parts: list[str] = []
    token_total = 0
    for chunk in sorted(chunks, key=lambda item: item.score, reverse=True):
        part = f"[Source: {chunk.filename}, Page {chunk.page_number or 'N/A'}]\n{chunk.text}"
        token_count = estimate_tokens(part)
        if token_total + token_count > max_context_tokens:
            break
        context_parts.append(part)
        token_total += token_count
    context = "\n\n".join(context_parts)
    confidence_note = (
        "The retrieved context has low similarity scores. Be conservative and say when the context is insufficient."
        if low_confidence
        else ""
    )
    return f"""<system>
You are a precise document assistant. Answer the user's question using ONLY the provided context.
If the context does not contain sufficient information, say: "I could not find relevant information in the provided documents."
Do NOT use any external knowledge. Cite your sources by referencing the document name and page number.
Keep the answer concise. Prefer 3 short bullet points or fewer unless the user explicitly asks for detail.
{confidence_note}
</system>

<context>
{context}
</context>

<conversation_history>
{history}
</conversation_history>

<question>
{query}
</question>

Answer:"""


def _format_history(messages: list[dict]) -> str:
    return "\n".join(f"{message['role']}: {message['content']}" for message in messages)


def _latency_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
