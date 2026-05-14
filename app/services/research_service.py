from __future__ import annotations

import re
import time
from collections.abc import Iterable

from app.config import settings
from app.ingestion.chunker import estimate_tokens
from app.models.chat import CitationValidation, Source
from app.models.research import ResearchRequest, ResearchResponse, ResearchStep
from app.services.citation_validator import CitationValidator
from app.services.llm_client import OllamaClient
from app.services.retrieval_engine import RetrievalEngine
from app.services.vector_store import RetrievedChunk

SPLIT_PATTERN = re.compile(r"\s+(?:and|versus|vs\.?|compared with|compare with)\s+", re.IGNORECASE)


class ResearchService:
    def __init__(
        self,
        retrieval_engine: RetrievalEngine,
        llm_client: OllamaClient,
        citation_validator: CitationValidator | None = None,
    ):
        self.retrieval_engine = retrieval_engine
        self.llm_client = llm_client
        self.citation_validator = citation_validator or CitationValidator()

    async def research(self, request: ResearchRequest) -> ResearchResponse:
        started = time.perf_counter()
        step_queries = plan_research_queries(request.query, request.max_steps)
        step_results: list[tuple[str, list[RetrievedChunk]]] = []
        for step_query in step_queries:
            chunks = await self.retrieval_engine.retrieve(
                step_query,
                top_k=request.top_k_per_step,
                document_ids=request.document_ids,
                min_score=settings.min_similarity_score,
            )
            if not chunks and settings.min_similarity_score > 0:
                chunks = await self.retrieval_engine.retrieve(
                    step_query,
                    top_k=request.top_k_per_step,
                    document_ids=request.document_ids,
                    min_score=0.0,
                )
            step_results.append((step_query, chunks))

        evidence = _dedupe_chunks(
            chunk for _, chunks in step_results for chunk in chunks
        )
        if not evidence:
            answer = "I could not find relevant information in the provided documents."
            return ResearchResponse(
                answer=answer,
                steps=_steps_from_results(step_results),
                sources=[],
                latency_ms=_latency_ms(started),
            )

        prompt = build_research_prompt(
            request.query,
            step_results,
            max_context_tokens=settings.max_context_tokens,
        )
        answer = await self.llm_client.generate(
            prompt,
            stream=False,
            temperature=settings.llm_temperature,
            top_p=settings.llm_top_p,
            num_ctx=settings.llm_num_ctx,
            num_predict=settings.llm_num_predict,
        )
        validation = _validate_citations(self.citation_validator, str(answer), evidence)
        return ResearchResponse(
            answer=str(answer),
            steps=_steps_from_results(step_results),
            sources=_sources_from_chunks(evidence),
            citation_validation=validation,
            latency_ms=_latency_ms(started),
        )


def plan_research_queries(query: str, max_steps: int = 3) -> list[str]:
    cleaned = re.sub(r"\s+", " ", query.strip())
    if not cleaned:
        return []

    planned = [cleaned]
    parts = [
        part.strip(" ?.,;:")
        for part in SPLIT_PATTERN.split(cleaned)
        if len(part.strip(" ?.,;:")) >= 4
    ]
    if len(parts) > 1:
        planned.extend(parts)
        planned.append(f"similarities differences {cleaned}")
    elif any(term in cleaned.lower() for term in ("why", "how", "impact", "risk")):
        planned.append(f"background evidence {cleaned}")
        planned.append(f"risks constraints {cleaned}")
    else:
        planned.append(f"key evidence {cleaned}")

    return _dedupe_strings(planned)[:max_steps]


def build_research_prompt(
    query: str,
    step_results: list[tuple[str, list[RetrievedChunk]]],
    max_context_tokens: int = 3000,
) -> str:
    context_parts: list[str] = []
    token_total = 0
    for step_index, (step_query, chunks) in enumerate(step_results, start=1):
        for chunk in sorted(chunks, key=lambda item: item.score, reverse=True):
            part = (
                f"[Step {step_index}: {step_query}]\n"
                f"[Source: {chunk.filename}, Page {chunk.page_number or 'N/A'}]\n"
                f"{chunk.text}"
            )
            token_count = estimate_tokens(part)
            if token_total + token_count > max_context_tokens:
                break
            context_parts.append(part)
            token_total += token_count
    context = "\n\n".join(context_parts)
    return f"""<system>
You are a careful research assistant for a document workspace.
Use ONLY the provided evidence.
If evidence is insufficient, say what is missing.
Write a concise research answer with:
- Answer
- Evidence
- Gaps or caveats
Cite document names and page numbers for each important point.
</system>

<evidence>
{context}
</evidence>

<question>
{query}
</question>

Research answer:"""


def _steps_from_results(step_results: list[tuple[str, list[RetrievedChunk]]]) -> list[ResearchStep]:
    return [
        ResearchStep(
            step=index,
            query=query,
            sources=_sources_from_chunks(chunks),
        )
        for index, (query, chunks) in enumerate(step_results, start=1)
    ]


def _sources_from_chunks(chunks: list[RetrievedChunk]) -> list[Source]:
    return [
        Source(
            document_id=chunk.document_id,
            filename=chunk.filename,
            page_number=chunk.page_number,
            chunk_text_preview=chunk.text[:200],
            score=round(chunk.score, 4),
        )
        for chunk in chunks
    ]


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


def _dedupe_chunks(chunks: Iterable[RetrievedChunk]) -> list[RetrievedChunk]:
    seen: set[tuple[str, int]] = set()
    deduped: list[RetrievedChunk] = []
    for chunk in chunks:
        key = (chunk.document_id, chunk.chunk_index)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)
    return deduped


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped


def _latency_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
