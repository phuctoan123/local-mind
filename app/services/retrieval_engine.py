from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.database import get_connection
from app.services.embedding_service import EmbeddingService
from app.services.hybrid_retriever import reciprocal_rank_fusion
from app.services.lexical_search import BM25Search
from app.services.query_rewriter import QueryRewriter
from app.services.reranker import LexicalReranker
from app.services.vector_store import RetrievedChunk, VectorStore


@dataclass(frozen=True)
class RetrievalTrace:
    original_query: str
    effective_query: str
    query_was_rewritten: bool
    mode: str
    vector_chunks: list[RetrievedChunk]
    bm25_chunks: list[RetrievedChunk]
    fused_chunks: list[RetrievedChunk]
    reranked_chunks: list[RetrievedChunk]
    fallback_chunks: list[RetrievedChunk]
    returned_chunks: list[RetrievedChunk]


class RetrievalEngine:
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
        lexical_search: BM25Search | None = None,
        query_rewriter: QueryRewriter | None = None,
        reranker: LexicalReranker | None = None,
    ):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.lexical_search = lexical_search or BM25Search()
        self.query_rewriter = query_rewriter or QueryRewriter()
        self.reranker = reranker or LexicalReranker()

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_ids: list[str] | None = None,
        min_score: float = 0.3,
    ) -> list[RetrievedChunk]:
        trace = await self.retrieve_debug(query, top_k, document_ids, min_score)
        return trace.returned_chunks

    async def retrieve_debug(
        self,
        query: str,
        top_k: int = 5,
        document_ids: list[str] | None = None,
        min_score: float = 0.3,
    ) -> RetrievalTrace:
        rewritten = self.query_rewriter.rewrite(query)
        effective_query = rewritten.query if settings.enable_query_rewriting else query.strip()
        candidate_k = max(
            top_k,
            settings.rerank_candidate_k if settings.enable_reranking else top_k,
        )
        mode = settings.retrieval_mode.lower()

        query_embedding = await self.embedding_service.embed_text(effective_query)
        vector_chunks: list[RetrievedChunk] = []
        bm25_chunks: list[RetrievedChunk] = []
        fused_chunks: list[RetrievedChunk] = []
        reranked_chunks: list[RetrievedChunk] = []
        fallback_chunks: list[RetrievedChunk] = []

        if mode == "hybrid":
            vector_chunks = self.vector_store.query(
                query_embedding,
                settings.vector_top_k,
                document_ids,
                min_score,
            )
            bm25_chunks = self.lexical_search.search(
                effective_query,
                settings.bm25_top_k,
                document_ids,
            )
            fused_chunks = reciprocal_rank_fusion(
                [vector_chunks, bm25_chunks],
                top_k=candidate_k,
                rrf_k=settings.rrf_k,
            )
        else:
            vector_chunks = self.vector_store.query(
                query_embedding,
                candidate_k,
                document_ids,
                min_score,
            )
            fused_chunks = vector_chunks

        returned_chunks = fused_chunks[:top_k]
        if fused_chunks and settings.enable_reranking:
            reranked_chunks = self.reranker.rerank(effective_query, fused_chunks, top_k)
            returned_chunks = reranked_chunks

        if not returned_chunks:
            fallback_chunks = keyword_retrieve(
                effective_query,
                top_k=top_k,
                document_ids=document_ids,
            )
            returned_chunks = fallback_chunks

        return RetrievalTrace(
            original_query=rewritten.original_query,
            effective_query=effective_query,
            query_was_rewritten=effective_query != rewritten.original_query,
            mode=mode,
            vector_chunks=vector_chunks,
            bm25_chunks=bm25_chunks,
            fused_chunks=fused_chunks,
            reranked_chunks=reranked_chunks,
            fallback_chunks=fallback_chunks,
            returned_chunks=returned_chunks,
        )


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
