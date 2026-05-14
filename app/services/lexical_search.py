from __future__ import annotations

import math
import re
from collections import Counter

from app.database import get_connection
from app.services.vector_store import RetrievedChunk


TOKEN_PATTERN = re.compile(r"[\wÀ-ỹ]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text) if len(token) >= 2]


class BM25Search:
    def search(
        self,
        query: str,
        top_k: int = 20,
        document_ids: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        query_terms = tokenize(query)
        if not query_terms:
            return []
        rows = self._load_rows(document_ids)
        if not rows:
            return []

        tokenized_docs = [tokenize(row["text"]) for row in rows]
        doc_freq: Counter[str] = Counter()
        for tokens in tokenized_docs:
            doc_freq.update(set(tokens))

        avg_doc_len = sum(len(tokens) for tokens in tokenized_docs) / max(len(tokenized_docs), 1)
        k1 = 1.5
        b = 0.75
        scored: list[tuple[float, RetrievedChunk]] = []
        for row, tokens in zip(rows, tokenized_docs, strict=False):
            if not tokens:
                continue
            frequencies = Counter(tokens)
            score = 0.0
            for term in query_terms:
                freq = frequencies.get(term, 0)
                if freq == 0:
                    continue
                idf = math.log(1 + (len(rows) - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
                denominator = freq + k1 * (1 - b + b * (len(tokens) / avg_doc_len))
                score += idf * ((freq * (k1 + 1)) / denominator)
            if score <= 0:
                continue
            scored.append(
                (
                    score,
                    RetrievedChunk(
                        document_id=row["document_id"],
                        filename=row["filename"],
                        page_number=row["page_number"],
                        chunk_index=row["chunk_index"],
                        text=row["text"],
                        score=score,
                        char_start=row["char_start"],
                        char_end=row["char_end"],
                    ),
                )
            )

        ranked = sorted(scored, key=lambda item: item[0], reverse=True)[:top_k]
        if not ranked:
            return []
        max_score = ranked[0][0] or 1.0
        return [
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
            for score, chunk in ranked
        ]

    @staticmethod
    def _load_rows(document_ids: list[str] | None = None):
        where = ""
        params: list[str] = []
        if document_ids:
            placeholders = ",".join("?" for _ in document_ids)
            where = f"WHERE c.document_id IN ({placeholders})"
            params.extend(document_ids)
        with get_connection() as conn:
            return conn.execute(
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
