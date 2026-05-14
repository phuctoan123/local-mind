from __future__ import annotations

import time
from collections.abc import AsyncIterator

from app.config import settings
from app.db.repositories.session_repo import SessionRepo
from app.ingestion.chunker import estimate_tokens
from app.models.chat import ChatRequest, ChatResponse, CitationValidation, Source
from app.services.citation_validator import CitationValidator
from app.services.llm_client import OllamaClient
from app.services.retrieval_engine import RetrievalEngine
from app.services.vector_store import RetrievedChunk


class RagService:
    def __init__(
        self,
        retrieval_engine: RetrievalEngine,
        llm_client: OllamaClient,
        session_repo: SessionRepo | None = None,
        citation_validator: CitationValidator | None = None,
    ):
        self.retrieval_engine = retrieval_engine
        self.llm_client = llm_client
        self.session_repo = session_repo
        self.citation_validator = citation_validator or CitationValidator()

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
        if _session_exists(self.session_repo, request.session_id):
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
        validation = _validate_citations(self.citation_validator, str(answer), chunks)
        if _session_exists(self.session_repo, request.session_id):
            self.session_repo.add_message(
                request.session_id,
                "assistant",
                str(answer),
                [source.model_dump() for source in sources],
            )
        return ChatResponse(
            answer=str(answer),
            sources=sources,
            citation_validation=validation,
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
        if _session_exists(self.session_repo, request.session_id):
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
        validation = _validate_citations(self.citation_validator, answer, chunks)
        if validation:
            yield {"type": "citation_validation", "validation": validation.model_dump()}
        if _session_exists(self.session_repo, request.session_id):
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
        "The retrieved context has low similarity scores. "
        "Be conservative and say when the context is insufficient."
        if low_confidence
        else ""
    )
    system_prompt = "\n".join(
        [
            "You are a precise document assistant.",
            "Answer the user's question using ONLY the provided context.",
            'If the context is insufficient, say: "I could not find relevant information '
            'in the provided documents."',
            "Do NOT use external knowledge.",
            "Cite sources by referencing the document name and page number.",
            "Keep the answer concise.",
            "Prefer 3 short bullet points or fewer unless the user asks for detail.",
        ]
    )
    return f"""<system>
{system_prompt}
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


def _session_exists(repo: SessionRepo | None, session_id: str | None) -> bool:
    return bool(session_id and repo and repo.exists(session_id))


def _validate_citations(
    validator: CitationValidator,
    answer: str,
    chunks: list[RetrievedChunk],
) -> CitationValidation | None:
    if not settings.enable_citation_validation:
        return None
    result = validator.validate(answer, chunks)
    return CitationValidation(
        status=result.status,
        coverage_score=result.coverage_score,
        cited_sources=result.cited_sources,
        supporting_sources=result.supporting_sources,
        warnings=result.warnings,
    )
