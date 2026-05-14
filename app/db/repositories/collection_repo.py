from __future__ import annotations

import uuid
from typing import Any


class CollectionRepo:
    def __init__(self, conn):
        self.conn = conn

    def create(self, name: str) -> dict[str, Any]:
        collection_id = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO collections (id, name) VALUES (?, ?)",
            (collection_id, name.strip()),
        )
        return self.get(collection_id)

    def get(self, collection_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT
                c.*,
                COUNT(cd.document_id) AS document_count
            FROM collections c
            LEFT JOIN collection_documents cd ON cd.collection_id = c.id
            WHERE c.id = ?
            GROUP BY c.id
            """,
            (collection_id,),
        ).fetchone()
        return dict(row) if row else None

    def list(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT
                c.*,
                COUNT(cd.document_id) AS document_count
            FROM collections c
            LEFT JOIN collection_documents cd ON cd.collection_id = c.id
            GROUP BY c.id
            ORDER BY c.created_at DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def delete(self, collection_id: str) -> None:
        self.conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))

    def add_document(self, collection_id: str, document_id: str) -> None:
        self.conn.execute(
            """
            INSERT OR IGNORE INTO collection_documents (collection_id, document_id)
            VALUES (?, ?)
            """,
            (collection_id, document_id),
        )
        self._touch(collection_id)

    def remove_document(self, collection_id: str, document_id: str) -> None:
        self.conn.execute(
            """
            DELETE FROM collection_documents
            WHERE collection_id = ? AND document_id = ?
            """,
            (collection_id, document_id),
        )
        self._touch(collection_id)

    def document_collection_ids(self, document_ids: list[str]) -> dict[str, list[str]]:
        if not document_ids:
            return {}
        placeholders = ",".join("?" for _ in document_ids)
        rows = self.conn.execute(
            f"""
            SELECT document_id, collection_id
            FROM collection_documents
            WHERE document_id IN ({placeholders})
            ORDER BY created_at DESC
            """,
            document_ids,
        ).fetchall()
        mapping = {document_id: [] for document_id in document_ids}
        for row in rows:
            mapping.setdefault(row["document_id"], []).append(row["collection_id"])
        return mapping

    def ready_document_ids(self, collection_id: str) -> list[str]:
        rows = self.conn.execute(
            """
            SELECT d.id
            FROM documents d
            JOIN collection_documents cd ON cd.document_id = d.id
            WHERE cd.collection_id = ? AND d.status = 'READY'
            ORDER BY d.created_at DESC
            """,
            (collection_id,),
        ).fetchall()
        return [row["id"] for row in rows]

    def _touch(self, collection_id: str) -> None:
        self.conn.execute(
            "UPDATE collections SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (collection_id,),
        )
