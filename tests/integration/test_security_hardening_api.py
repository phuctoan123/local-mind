from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from app.config import settings


def test_api_key_required_for_api_routes_when_configured(integration):
    object.__setattr__(settings, "api_key", "test-secret")

    missing = integration.client.get("/api/v1/documents")
    wrong = integration.client.get("/api/v1/documents", headers={"X-API-Key": "wrong"})
    ok = integration.client.get("/api/v1/documents", headers={"X-API-Key": "test-secret"})

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert missing.json() == {"error": "unauthorized", "message": "Invalid or missing API key"}
    assert ok.status_code == 200


def test_api_key_middleware_does_not_protect_openai_compat_route(integration):
    object.__setattr__(settings, "api_key", "test-secret")

    response = integration.client.options("/v1/chat/completions")

    assert response.status_code in {200, 405}
    assert response.status_code != 401


def test_cors_allows_configured_origin(integration):
    response = integration.client.options(
        "/api/v1/documents",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_rejects_unconfigured_origin(integration):
    response = integration.client.options(
        "/api/v1/documents",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_response_includes_request_id_header(integration):
    response = integration.client.get(
        "/api/v1/documents",
        headers={"X-Request-ID": "qa-request-1"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "qa-request-1"


def test_upload_rejects_docx_with_unsafe_compression_ratio(integration):
    object.__setattr__(settings, "max_docx_compression_ratio", 2)

    response = integration.client.post(
        "/api/v1/upload",
        files={
            "file": (
                "unsafe.docx",
                _docx_bytes({"word/payload.txt": "A" * 100_000}),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "unsafe_archive"


def _docx_bytes(extra_entries: dict[str, str] | None = None) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("word/document.xml", "<w:document />")
        for name, content in (extra_entries or {}).items():
            archive.writestr(name, content)
    return buffer.getvalue()
