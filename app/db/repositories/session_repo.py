from __future__ import annotations

import json
import uuid
from typing import Any


class SessionRepo:
    def __init__(self, conn):
        self.conn = conn

    def create(self, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        session_id = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO sessions (id, metadata) VALUES (?, ?)",
            (session_id, json.dumps(metadata or {})),
        )
        row = self.conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return dict(row)

    def exists(self, session_id: str) -> bool:
        return bool(self.conn.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)).fetchone())

    def touch(self, session_id: str) -> None:
        self.conn.execute(
            "UPDATE sessions SET last_active = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,),
        )

    def delete(self, session_id: str) -> None:
        self.conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO messages (id, session_id, role, content, sources)
            VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), session_id, role, content, json.dumps(sources or [])),
        )
        self.touch(session_id)

    def history(self, session_id: str, limit: int = 10) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT role, content, sources, created_at
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (session_id, limit * 2),
        ).fetchall()
        return [dict(row) for row in reversed(rows)]
