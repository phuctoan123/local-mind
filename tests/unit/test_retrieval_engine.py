import asyncio
from types import SimpleNamespace

from app.services.retrieval_engine import RetrievalEngine
from app.services.vector_store import RetrievedChunk


def test_retrieve_debug_exposes_rewrite_and_rerank_stages(monkeypatch):
    monkeypatch.setattr(
        "app.services.retrieval_engine.settings",
        SimpleNamespace(
            retrieval_mode="hybrid",
            enable_query_rewriting=True,
            enable_reranking=True,
            rerank_candidate_k=5,
            vector_top_k=5,
            bm25_top_k=5,
            rrf_k=60,
        ),
    )
    engine = RetrievalEngine(
        vector_store=FakeVectorStore(),
        embedding_service=FakeEmbeddingService(),
        lexical_search=FakeLexicalSearch(),
    )

    trace = asyncio.run(engine.retrieve_debug("Please tell me about notice period", top_k=1))

    assert trace.effective_query == "notice period"
    assert trace.query_was_rewritten is True
    assert trace.vector_chunks
    assert trace.bm25_chunks
    assert trace.fused_chunks
    assert trace.reranked_chunks
    assert trace.returned_chunks[0].chunk_index == 2


class FakeEmbeddingService:
    async def embed_text(self, query: str) -> list[float]:
        assert query == "notice period"
        return [1.0, 0.0]


class FakeVectorStore:
    def query(self, *_args, **_kwargs) -> list[RetrievedChunk]:
        return [
            _chunk(1, "General agreement language.", 0.95),
            _chunk(2, "The notice period is 30 days.", 0.7),
        ]


class FakeLexicalSearch:
    def search(self, query: str, *_args, **_kwargs) -> list[RetrievedChunk]:
        assert query == "notice period"
        return [_chunk(2, "The notice period is 30 days.", 1.0)]


def _chunk(index: int, text: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        document_id="doc-1",
        filename="agreement.pdf",
        page_number=1,
        chunk_index=index,
        text=text,
        score=score,
        char_start=0,
        char_end=len(text),
    )
