from __future__ import annotations

import re
from dataclasses import dataclass

LEADING_FILLER_PATTERNS = (
    re.compile(r"^\s*(please|pls)\b[:,]?\s*", re.IGNORECASE),
    re.compile(r"^\s*(can|could|would)\s+you\b[:,]?\s*", re.IGNORECASE),
    re.compile(r"^\s*(tell|show|explain)\s+me\s+(about\s+)?", re.IGNORECASE),
    re.compile(r"^\s*(question|query)\s*:\s*", re.IGNORECASE),
)
WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True)
class RewrittenQuery:
    original_query: str
    query: str

    @property
    def was_rewritten(self) -> bool:
        return self.query != self.original_query.strip()


class QueryRewriter:
    """Small deterministic rewrite pass for retrieval-facing queries."""

    def rewrite(self, query: str) -> RewrittenQuery:
        original = query.strip()
        rewritten = WHITESPACE_PATTERN.sub(" ", original)
        for pattern in LEADING_FILLER_PATTERNS:
            rewritten = pattern.sub("", rewritten)
        rewritten = rewritten.strip(" \t\r\n")
        return RewrittenQuery(
            original_query=original,
            query=rewritten or original,
        )
