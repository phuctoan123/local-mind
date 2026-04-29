from __future__ import annotations

from app.database import get_connection
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import RetrievedChunk, VectorStore


class RetrievalEngine:
    def __init__(self, vector_store: VectorStore, embedding_service: EmbeddingService):
        self.vector_store = vector_store
        self.embedding_service = embedding_service

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_ids: list[str] | None = None,
        min_score: float = 0.3,
    ) -> list[RetrievedChunk]:
        query_embedding = await self.embedding_service.embed_text(query)
        chunks = self.vector_store.query(query_embedding, top_k, document_ids, min_score)
        if chunks:
            return chunks
        return keyword_retrieve(query, top_k=top_k, document_ids=document_ids)


def keyword_retrieve(
    query: str,
    top_k: int = 5,
    document_ids: list[str] | None = None,
) -> list[RetrievedChunk]:
    terms = [term.lower() for term in query.split() if len(term) >= 3]
    if not terms:
        return []
    where = ""
    params: list[str] = []
    if document_ids:
        placeholders = ",".join("?" for _ in document_ids)
        where = f"WHERE c.document_id IN ({placeholders})"
        params.extend(document_ids)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT
                c.document_id,
                d.original_name AS filename,
                c.page_number,
                c.chunk_index,
                c.text,
                c.char_start,
                c.char_end
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            {where}
            """,
            params,
        ).fetchall()

    scored: list[RetrievedChunk] = []
    for row in rows:
        text = row["text"]
        lower_text = text.lower()
        hits = sum(lower_text.count(term) for term in terms)
        if hits <= 0:
            continue
        score = min(1.0, hits / max(len(terms), 1))
        scored.append(
            RetrievedChunk(
                document_id=row["document_id"],
                filename=row["filename"],
                page_number=row["page_number"],
                chunk_index=row["chunk_index"],
                text=text,
                score=score,
                char_start=row["char_start"],
                char_end=row["char_end"],
            )
        )
    return sorted(scored, key=lambda chunk: chunk.score, reverse=True)[:top_k]
