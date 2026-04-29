from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile
from starlette import status

from app.config import settings
from app.database import get_connection
from app.db.repositories.chunk_repo import ChunkRepo
from app.db.repositories.document_repo import DocumentRepo
from app.dependencies import get_vector_store
from app.ingestion.worker import process_document
from app.models.document import (
    ChunkPreview,
    DocumentChunksResponse,
    DocumentListResponse,
    DocumentResponse,
    UploadResponse,
)
from app.utils.file_utils import detect_mime_type, extension_allowed, secure_filename

router = APIRouter(tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    original_name = file.filename or "document"
    if not extension_allowed(original_name, settings.allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "unsupported_format",
                "message": f"File type is not supported: {original_name}",
                "allowed_types": list(settings.allowed_extensions),
            },
        )

    contents = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": "file_too_large",
                "message": f"File exceeds maximum allowed size of {settings.max_upload_size_mb} MB",
                "max_bytes": max_bytes,
                "received_bytes": len(contents),
            },
        )

    document_id = str(uuid.uuid4())
    safe_name = secure_filename(original_name)
    suffix = Path(safe_name).suffix.lower()
    stored_name = f"{document_id}{suffix}"
    file_path = settings.raw_files_dir / stored_name
    settings.raw_files_dir.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(contents)

    doc = {
        "id": document_id,
        "filename": stored_name,
        "original_name": safe_name,
        "file_path": str(file_path.resolve()),
        "file_size": len(contents),
        "mime_type": detect_mime_type(safe_name),
        "status": "PENDING",
    }
    with get_connection() as conn:
        DocumentRepo(conn).create(doc)

    background_tasks.add_task(process_document, document_id)
    return UploadResponse(
        document_id=document_id,
        filename=safe_name,
        file_size=len(contents),
        status="PENDING",
        message="Document uploaded successfully. Processing in background.",
    )


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    with get_connection() as conn:
        total, documents = DocumentRepo(conn).list(status_filter, page, page_size)
    return DocumentListResponse(
        total=total,
        page=page,
        page_size=page_size,
        documents=[DocumentResponse(**document) for document in documents],
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str):
    with get_connection() as conn:
        document = DocumentRepo(conn).get(document_id)
    if not document:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Document '{document_id}' does not exist"},
        )
    return DocumentResponse(**document)


@router.get("/documents/{document_id}/chunks", response_model=DocumentChunksResponse)
def get_document_chunks(document_id: str, limit: int = Query(default=5, ge=1, le=50)):
    with get_connection() as conn:
        document = DocumentRepo(conn).get(document_id)
        if not document:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": f"Document '{document_id}' does not exist"},
            )
        chunks = ChunkRepo(conn).list_by_document(document_id)[:limit]
    return DocumentChunksResponse(
        document_id=document_id,
        chunks=[
            ChunkPreview(
                chunk_index=chunk["chunk_index"],
                page_number=chunk["page_number"],
                text=chunk["text"][:1000],
            )
            for chunk in chunks
        ],
    )


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: str):
    with get_connection() as conn:
        doc_repo = DocumentRepo(conn)
        document = doc_repo.get(document_id)
        if not document:
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": f"Document '{document_id}' does not exist"},
            )
        if document["status"] == "PROCESSING":
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "conflict",
                    "message": "Document is currently being processed.",
                },
            )

    get_vector_store().delete_by_document(document_id)
    with get_connection() as conn:
        ChunkRepo(conn).delete_by_document(document_id)
        DocumentRepo(conn).delete(document_id)

    try:
        Path(document["file_path"]).unlink(missing_ok=True)
    except OSError:
        pass
    return None
