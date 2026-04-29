from app.services.rag_service import build_prompt
from app.services.vector_store import RetrievedChunk


def test_prompt_contains_context_and_query():
    prompt = build_prompt(
        "What is the notice period?",
        [
            RetrievedChunk(
                document_id="doc-1",
                filename="agreement.pdf",
                page_number=2,
                chunk_index=0,
                text="The notice period is 30 days.",
                score=0.9,
                char_start=0,
                char_end=33,
            )
        ],
    )
    assert "agreement.pdf" in prompt
    assert "The notice period is 30 days." in prompt
    assert "What is the notice period?" in prompt


def test_prompt_truncates_context():
    chunks = [
        RetrievedChunk(
            document_id=f"doc-{index}",
            filename=f"doc-{index}.txt",
            page_number=1,
            chunk_index=index,
            text="x" * 1000,
            score=1.0 - (index / 100),
            char_start=0,
            char_end=1000,
        )
        for index in range(10)
    ]
    prompt = build_prompt("question", chunks, max_context_tokens=300)
    assert "doc-0.txt" in prompt
    assert "doc-9.txt" not in prompt
