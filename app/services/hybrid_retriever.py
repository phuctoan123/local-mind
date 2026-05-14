from __future__ import annotations

from app.services.vector_store import RetrievedChunk


def reciprocal_rank_fusion(
    result_sets: list[list[RetrievedChunk]],
    top_k: int,
    rrf_k: int = 60,
) -> list[RetrievedChunk]:
    scores: dict[tuple[str, int], float] = {}
    chunks: dict[tuple[str, int], RetrievedChunk] = {}
    for results in result_sets:
        for rank, chunk in enumerate(results, start=1):
            key = (chunk.document_id, chunk.chunk_index)
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank)
            chunks[key] = chunk
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
    if not ranked:
        return []
    max_score = ranked[0][1] or 1.0
    fused: list[RetrievedChunk] = []
    for key, score in ranked:
        chunk = chunks[key]
        fused.append(
            RetrievedChunk(
                document_id=chunk.document_id,
                filename=chunk.filename,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                score=round(score / max_score, 4),
                char_start=chunk.char_start,
                char_end=chunk.char_end,
            )
        )
    return fused
