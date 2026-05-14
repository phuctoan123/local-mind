from app.services.reranker import LexicalReranker
from app.services.vector_store import RetrievedChunk


def test_reranker_promotes_better_query_term_coverage():
    chunks = [
        _chunk(0, "The agreement mentions a general policy.", 0.95),
        _chunk(1, "The notice period is 30 days after termination.", 0.7),
    ]

    reranked = LexicalReranker().rerank("notice period termination", chunks, top_k=2)

    assert reranked[0].chunk_index == 1
    assert reranked[0].score > reranked[1].score


def test_reranker_deduplicates_chunks():
    chunks = [
        _chunk(0, "The notice period is 30 days.", 0.7),
        _chunk(0, "The notice period is 30 days.", 0.6),
    ]

    reranked = LexicalReranker().rerank("notice period", chunks, top_k=5)

    assert len(reranked) == 1


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
