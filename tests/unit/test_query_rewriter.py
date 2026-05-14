from app.services.query_rewriter import QueryRewriter


def test_query_rewriter_removes_common_leading_filler():
    rewritten = QueryRewriter().rewrite("Please tell me about the notice period")

    assert rewritten.query == "the notice period"
    assert rewritten.was_rewritten is True


def test_query_rewriter_preserves_meaningful_query():
    rewritten = QueryRewriter().rewrite("termination clause notice period")

    assert rewritten.query == "termination clause notice period"
    assert rewritten.was_rewritten is False
