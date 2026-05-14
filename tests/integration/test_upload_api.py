from app.database import get_connection


def test_upload_txt_runs_background_ingestion(integration):
    response = integration.client.post(
        "/api/v1/upload",
        files={
            "file": (
                "contract.txt",
                b"Contract termination requires thirty days notice and manager approval.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "contract.txt"
    assert payload["status"] == "PENDING"

    document = integration.get_document(payload["document_id"])
    assert document["status"] == "READY"
    assert document["chunk_count"] >= 1
    assert (integration.raw_files_dir / document["filename"]).exists()

    with get_connection() as conn:
        chunk_count = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE document_id = ?",
            (payload["document_id"],),
        ).fetchone()[0]
        vector_count = conn.execute(
            "SELECT COUNT(*) FROM vectors WHERE document_id = ?",
            (payload["document_id"],),
        ).fetchone()[0]
    assert chunk_count >= 1
    assert vector_count >= 1


def test_upload_rejects_spoofed_pdf(integration):
    response = integration.client.post(
        "/api/v1/upload",
        files={"file": ("spoof.pdf", b"not actually a pdf", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "invalid_file_signature"


def test_upload_rejects_unsupported_extension(integration):
    response = integration.client.post(
        "/api/v1/upload",
        files={"file": ("payload.exe", b"hello", "application/octet-stream")},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "unsupported_format"


def test_upload_rejects_file_larger_than_configured_limit(integration):
    response = integration.client.post(
        "/api/v1/upload",
        files={"file": ("large.txt", b"x" * (1024 * 1024 + 1), "text/plain")},
    )

    assert response.status_code == 413
    assert response.json()["detail"]["error"] == "file_too_large"
