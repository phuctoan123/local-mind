from app.services.citation_validator import CitationValidator
from app.services.vector_store import RetrievedChunk


def test_citation_validator_marks_answer_supported_with_source_reference():
    answer = "The notice period is 30 days according to agreement.pdf page 2."

    result = CitationValidator().validate(answer, [_chunk("The notice period is 30 days.", 2)])

    assert result.status == "supported"
    assert result.cited_sources == 1
    assert result.coverage_score > 0.25
    assert not result.warnings


def test_citation_validator_warns_when_answer_does_not_cite_source():
    answer = "The notice period is 30 days."

    result = CitationValidator().validate(answer, [_chunk("The notice period is 30 days.", 2)])

    assert result.status == "partially_supported"
    assert result.cited_sources == 0
    assert "no_explicit_source_reference" in result.warnings


def test_citation_validator_marks_unrelated_answer_unsupported():
    answer = "The contract renews automatically every January."

    result = CitationValidator().validate(answer, [_chunk("The notice period is 30 days.", 2)])

    assert result.status == "unsupported"
    assert "low_answer_context_overlap" in result.warnings


def _chunk(text: str, page_number: int) -> RetrievedChunk:
    return RetrievedChunk(
        document_id="doc-1",
        filename="agreement.pdf",
        page_number=page_number,
        chunk_index=0,
        text=text,
        score=0.9,
        char_start=0,
        char_end=len(text),
    )
