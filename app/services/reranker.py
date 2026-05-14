from __future__ import annotations

from collections import Counter

from app.services.lexical_search import tokenize
from app.services.vector_store import RetrievedChunk


class LexicalReranker:
    """Local reranker that rewards source score, token coverage, and phrase hits."""

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []
        query_terms = tokenize(query)
        if not query_terms:
            return chunks[:top_k]

        unique_terms = set(query_terms)
        query_phrase = " ".join(query_terms)
        ranked: list[tuple[float, RetrievedChunk]] = []
        for chunk in _dedupe_chunks(chunks):
            chunk_terms = tokenize(chunk.text)
            if not chunk_terms:
                ranked.append((chunk.score, chunk))
                continue

            frequencies = Counter(chunk_terms)
            matched_terms = unique_terms.intersection(frequencies)
            coverage = len(matched_terms) / max(len(unique_terms), 1)
            density = sum(frequencies[term] for term in matched_terms) / max(len(chunk_terms), 1)
            phrase_bonus = 1.0 if query_phrase and query_phrase in " ".join(chunk_terms) else 0.0
            final_score = (
                (0.65 * _clamp_score(chunk.score))
                + (0.25 * coverage)
                + (0.05 * min(density * 10, 1.0))
                + (0.05 * phrase_bonus)
            )
            ranked.append((final_score, chunk))

        sorted_items = sorted(ranked, key=lambda item: item[0], reverse=True)[:top_k]
        return [
            RetrievedChunk(
                document_id=chunk.document_id,
                filename=chunk.filename,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                score=round(score, 4),
                char_start=chunk.char_start,
                char_end=chunk.char_end,
            )
            for score, chunk in sorted_items
        ]


def _dedupe_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    seen: set[tuple[str, int]] = set()
    deduped: list[RetrievedChunk] = []
    for chunk in chunks:
        key = (chunk.document_id, chunk.chunk_index)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)
    return deduped


def _clamp_score(score: float) -> float:
    return max(0.0, min(score, 1.0))
