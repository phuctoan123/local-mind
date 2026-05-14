from __future__ import annotations

from pydantic import BaseModel, Field


class CollectionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)


class CollectionResponse(BaseModel):
    id: str
    name: str
    document_count: int = 0
    created_at: str
    updated_at: str


class CollectionListResponse(BaseModel):
    collections: list[CollectionResponse]


class CollectionDocumentResponse(BaseModel):
    collection_id: str
    document_id: str
    assigned: bool


class CollectionReadyDocumentsResponse(BaseModel):
    collection_id: str
    document_ids: list[str]
