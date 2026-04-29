from __future__ import annotations

from typing import Any


class DocumentRepo:
    def __init__(self, conn):
        self.conn = conn

    def create(self, doc: dict[str, Any]) -> dict[str, Any]:
        self.conn.execute(
            """
            INSERT INTO documents (
                id, filename, original_name, file_path, file_size, mime_type, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc["id"],
                doc["filename"],
                doc["original_name"],
                doc["file_path"],
                doc["file_size"],
                doc["mime_type"],
                doc.get("status", "PENDING"),
            ),
        )
        return self.get(doc["id"])

    def get(self, document_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
        return dict(row) if row else None

    def list(
        self,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[int, list[dict[str, Any]]]:
        where = ""
        params: list[Any] = []
        if status:
            where = "WHERE status = ?"
            params.append(status)
        total = self.conn.execute(f"SELECT COUNT(*) FROM documents {where}", params).fetchone()[0]
        offset = max(page - 1, 0) * page_size
        rows = self.conn.execute(
            f"SELECT * FROM documents {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            [*params, page_size, offset],
        ).fetchall()
        return total, [dict(row) for row in rows]

    def update_status(
        self,
        document_id: str,
        status: str,
        chunk_count: int | None = None,
        error_message: str | None = None,
    ) -> None:
        self.conn.execute(
            """
            UPDATE documents
            SET status = ?,
                chunk_count = COALESCE(?, chunk_count),
                error_message = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, chunk_count, error_message, document_id),
        )

    def delete(self, document_id: str) -> None:
        self.conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))

    def count_ready(self) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM documents WHERE status = 'READY'"
        ).fetchone()[0]
