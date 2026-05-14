import sqlite3

from app.database import run_migrations
from app.db.repositories.collection_repo import CollectionRepo


def test_collection_repo_assigns_and_maps_documents():
    conn = _memory_conn()
    repo = CollectionRepo(conn)
    collection = repo.create("Contracts")
    _create_document(conn, "doc-1")

    repo.add_document(collection["id"], "doc-1")
    mapping = repo.document_collection_ids(["doc-1"])

    assert mapping["doc-1"] == [collection["id"]]
    assert repo.ready_document_ids(collection["id"]) == ["doc-1"]
    assert repo.list()[0]["document_count"] == 1

    repo.remove_document(collection["id"], "doc-1")

    assert repo.document_collection_ids(["doc-1"])["doc-1"] == []


def _memory_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    run_migrations(conn)
    return conn


def _create_document(conn, document_id: str) -> None:
    conn.execute(
        """
        INSERT INTO documents (
            id, filename, original_name, file_path, file_size, mime_type, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (document_id, "doc.txt", "doc.txt", "/tmp/doc.txt", 10, "text/plain", "READY"),
    )
