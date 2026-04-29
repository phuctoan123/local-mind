from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    pending = "PENDING"
    processing = "PROCESSING"
    ready = "READY"
    failed = "FAILED"


class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_name: str
    file_size: int
    mime_type: str
    status: DocumentStatus
    chunk_count: int = 0
    error_message: str | None = None
    created_at: str
    updated_at: str


class ChunkPreview(BaseModel):
    chunk_index: int
    page_number: int | None = None
    text: str


class DocumentChunksResponse(BaseModel):
    document_id: str
    chunks: list[ChunkPreview]


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    file_size: int
    status: DocumentStatus
    message: str


class DocumentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    documents: list[DocumentResponse]


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: dict[str, Any] | None = Field(default=None)
