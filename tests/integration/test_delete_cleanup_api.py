from pathlib import Path

from app.database import get_connection


def test_delete_document_removes_file_chunks_vectors_and_collection_membership(integration):
    document = integration.seed_document(
        filename="cleanup-contract.txt",
        text="Contract cleanup should remove chunks, vectors, files, and collection membership.",
    )
    file_path = Path(document["file_path"])
    collection = integration.client.post("/api/v1/collections", json={"name": "Cleanup"}).json()
    add_response = integration.client.put(
        f"/api/v1/collections/{collection['id']}/documents/{document['id']}"
    )

    assert add_response.status_code == 200
    assert file_path.exists()
    assert _count("chunks", document["id"]) > 0
    assert _count("vectors", document["id"]) > 0
    assert _membership_count(collection["id"], document["id"]) == 1

    response = integration.client.delete(f"/api/v1/documents/{document['id']}")

    assert response.status_code == 204
    assert integration.get_document(document["id"]) is None
    assert not file_path.exists()
    assert _count("chunks", document["id"]) == 0
    assert _count("vectors", document["id"]) == 0
    assert _membership_count(collection["id"], document["id"]) == 0
    assert integration.client.get(f"/api/v1/documents/{document['id']}").status_code == 404


def test_delete_processing_document_returns_conflict_and_preserves_file(integration):
    document = integration.seed_document(
        filename="processing.txt",
        text="This document is still processing and should not be deleted.",
        status="PROCESSING",
    )
    file_path = Path(document["file_path"])

    response = integration.client.delete(f"/api/v1/documents/{document['id']}")

    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "conflict"
    assert file_path.exists()
    preserved = integration.get_document(document["id"])
    assert preserved is not None
    assert preserved["status"] == "PROCESSING"


def _count(table: str, document_id: str) -> int:
    with get_connection() as conn:
        return conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE document_id = ?",
            (document_id,),
        ).fetchone()[0]


def _membership_count(collection_id: str, document_id: str) -> int:
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT COUNT(*)
            FROM collection_documents
            WHERE collection_id = ? AND document_id = ?
            """,
            (collection_id, document_id),
        ).fetchone()[0]
