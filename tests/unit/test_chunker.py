from app.ingestion.chunker import RecursiveChunker, estimate_tokens
from app.ingestion.parsers.base import ParsedPage


def test_empty_document_returns_empty_list():
    assert RecursiveChunker().chunk([]) == []


def test_chunk_size_is_respected_with_overlap():
    text = " ".join(["contract termination notice period"] * 500)
    chunks = RecursiveChunker(chunk_size=64, chunk_overlap=8, min_chunk_length=10).chunk(
        [ParsedPage(page_number=1, text=text, metadata={})]
    )
    assert len(chunks) > 1
    assert all(chunk.token_count <= 64 for chunk in chunks)
    assert chunks[1].char_start < chunks[0].char_end


def test_min_length_filter_discards_tiny_chunks():
    chunks = RecursiveChunker(chunk_size=64, chunk_overlap=8, min_chunk_length=50).chunk(
        [ParsedPage(page_number=1, text="short", metadata={})]
    )
    assert chunks == []


def test_estimate_tokens_has_floor():
    assert estimate_tokens("") == 1
