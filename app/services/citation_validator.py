from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.services.lexical_search import tokenize
from app.services.vector_store import RetrievedChunk

INSUFFICIENT_CONTEXT_TEXT = "i could not find relevant information"
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


@dataclass(frozen=True)
class CitationValidationResult:
    status: str
    coverage_score: float
    cited_sources: int
    supporting_sources: list[str]
    warnings: list[str]


class CitationValidator:
    def validate(self, answer: str, chunks: list[RetrievedChunk]) -> CitationValidationResult:
        answer_text = answer.strip()
        if not answer_text or not chunks:
            return CitationValidationResult(
                status="not_applicable",
                coverage_score=0.0,
                cited_sources=0,
                supporting_sources=[],
                warnings=["no_answer_or_sources"],
            )
        if INSUFFICIENT_CONTEXT_TEXT in answer_text.lower():
            return CitationValidationResult(
                status="not_applicable",
                coverage_score=0.0,
                cited_sources=0,
                supporting_sources=[],
                warnings=["answer_declares_insufficient_context"],
            )

        answer_terms = _content_terms(answer_text)
        context_terms = _content_terms("\n".join(chunk.text for chunk in chunks))
        coverage = len(answer_terms.intersection(context_terms)) / max(len(answer_terms), 1)

        cited_sources = _count_explicit_source_references(answer_text, chunks)
        supporting_sources = _supporting_source_labels(answer_terms, chunks)
        warnings: list[str] = []
        if coverage < 0.12:
            warnings.append("low_answer_context_overlap")
        if cited_sources == 0:
            warnings.append("no_explicit_source_reference")

        if coverage >= 0.25 and cited_sources > 0:
            status = "supported"
        elif coverage >= 0.12:
            status = "partially_supported"
        else:
            status = "unsupported"

        return CitationValidationResult(
            status=status,
            coverage_score=round(coverage, 4),
            cited_sources=cited_sources,
            supporting_sources=supporting_sources,
            warnings=warnings,
        )


def _content_terms(text: str) -> set[str]:
    return {term for term in tokenize(text) if len(term) >= 3 and term not in STOPWORDS}


def _count_explicit_source_references(answer: str, chunks: list[RetrievedChunk]) -> int:
    normalized_answer = _normalize(answer)
    cited: set[tuple[str, int]] = set()
    for chunk in chunks:
        filename = _normalize(chunk.filename)
        stem = _normalize(Path(chunk.filename).stem)
        page = str(chunk.page_number) if chunk.page_number is not None else ""
        has_filename = bool(filename and filename in normalized_answer)
        has_stem = bool(stem and stem in normalized_answer)
        has_page = bool(
            page and re.search(rf"\b(page|p)\.?\s*{re.escape(page)}\b", normalized_answer)
        )
        if has_filename or has_stem or has_page:
            cited.add((chunk.document_id, chunk.chunk_index))
    return len(cited)


def _supporting_source_labels(answer_terms: set[str], chunks: list[RetrievedChunk]) -> list[str]:
    labels: list[str] = []
    for chunk in chunks:
        chunk_terms = _content_terms(chunk.text)
        if not chunk_terms:
            continue
        overlap = len(answer_terms.intersection(chunk_terms)) / max(len(answer_terms), 1)
        if overlap >= 0.12:
            page = chunk.page_number if chunk.page_number is not None else "N/A"
            labels.append(f"{chunk.filename} p.{page}")
    return labels[:5]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()
