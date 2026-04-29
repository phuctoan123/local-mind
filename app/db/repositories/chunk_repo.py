from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.ingestion.chunker import Chunk


class ChunkRepo:
    def __init__(self, conn):
        self.conn = conn

    def insert_many(self, document_id: str, chunks: list[Chunk]) -> None:
        self.conn.executemany(
            """
            INSERT OR REPLACE INTO chunks (
                id, document_id, chunk_index, text, token_count, page_number, char_start, char_end
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    f"{document_id}_{chunk.chunk_index}",
                    document_id,
                    chunk.chunk_index,
                    chunk.text,
                    chunk.token_count,
                    chunk.source_page,
                    chunk.char_start,
                    chunk.char_end,
                )
                for chunk in chunks
            ],
        )

    def list_by_document(self, document_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index",
            (document_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def delete_by_document(self, document_id: str) -> None:
        self.conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
