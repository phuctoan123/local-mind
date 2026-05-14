from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException

from app.database import get_connection
from app.db.repositories.collection_repo import CollectionRepo
from app.db.repositories.document_repo import DocumentRepo
from app.models.collection import (
    CollectionCreateRequest,
    CollectionDocumentResponse,
    CollectionListResponse,
    CollectionReadyDocumentsResponse,
    CollectionResponse,
)

router = APIRouter(tags=["collections"])


@router.get("/collections", response_model=CollectionListResponse)
def list_collections():
    with get_connection() as conn:
        collections = CollectionRepo(conn).list()
    return CollectionListResponse(
        collections=[CollectionResponse(**collection) for collection in collections]
    )


@router.post("/collections", response_model=CollectionResponse, status_code=201)
def create_collection(request: CollectionCreateRequest):
    name = request.name.strip()
    if not name:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_name", "message": "Collection name cannot be empty."},
        )
    try:
        with get_connection() as conn:
            collection = CollectionRepo(conn).create(name)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "duplicate_collection",
                "message": f"Collection '{name}' already exists.",
            },
        ) from exc
    return CollectionResponse(**collection)


@router.delete("/collections/{collection_id}", status_code=204)
def delete_collection(collection_id: str):
    with get_connection() as conn:
        repo = CollectionRepo(conn)
        if not repo.get(collection_id):
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": "Collection does not exist."},
            )
        repo.delete(collection_id)
    return None


@router.put(
    "/collections/{collection_id}/documents/{document_id}",
    response_model=CollectionDocumentResponse,
)
def add_document_to_collection(collection_id: str, document_id: str):
    with get_connection() as conn:
        collection_repo = CollectionRepo(conn)
        _ensure_collection_and_document(
            collection_repo,
            DocumentRepo(conn),
            collection_id,
            document_id,
        )
        collection_repo.add_document(collection_id, document_id)
    return CollectionDocumentResponse(
        collection_id=collection_id,
        document_id=document_id,
        assigned=True,
    )


@router.delete(
    "/collections/{collection_id}/documents/{document_id}",
    response_model=CollectionDocumentResponse,
)
def remove_document_from_collection(collection_id: str, document_id: str):
    with get_connection() as conn:
        collection_repo = CollectionRepo(conn)
        _ensure_collection_and_document(
            collection_repo,
            DocumentRepo(conn),
            collection_id,
            document_id,
        )
        collection_repo.remove_document(collection_id, document_id)
    return CollectionDocumentResponse(
        collection_id=collection_id,
        document_id=document_id,
        assigned=False,
    )


@router.get(
    "/collections/{collection_id}/ready-documents",
    response_model=CollectionReadyDocumentsResponse,
)
def get_collection_ready_documents(collection_id: str):
    with get_connection() as conn:
        repo = CollectionRepo(conn)
        if not repo.get(collection_id):
            raise HTTPException(
                status_code=404,
                detail={"error": "not_found", "message": "Collection does not exist."},
            )
        document_ids = repo.ready_document_ids(collection_id)
    return CollectionReadyDocumentsResponse(
        collection_id=collection_id,
        document_ids=document_ids,
    )


def _ensure_collection_and_document(
    collection_repo: CollectionRepo,
    document_repo: DocumentRepo,
    collection_id: str,
    document_id: str,
) -> None:
    if not collection_repo.get(collection_id):
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Collection does not exist."},
        )
    if not document_repo.get(document_id):
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Document does not exist."},
        )
