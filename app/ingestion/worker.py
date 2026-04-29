from __future__ import annotations

from app.config import settings
from app.database import get_connection
from app.db.repositories.chunk_repo import ChunkRepo
from app.db.repositories.document_repo import DocumentRepo
from app.dependencies import get_embedding_service
from app.ingestion.chunker import RecursiveChunker
from app.ingestion.parsers import parser_for_mime_type
from app.services.vector_store import VectorStore


async def process_document(document_id: str) -> None:
    with get_connection() as conn:
        doc_repo = DocumentRepo(conn)
        document = doc_repo.get(document_id)
        if not document:
            return
        doc_repo.update_status(document_id, "PROCESSING")

    try:
        parser = parser_for_mime_type(document["mime_type"])
        pages = parser.parse(document["file_path"])
        chunker = RecursiveChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            min_chunk_length=settings.min_chunk_length,
        )
        chunks = chunker.chunk(pages)
        embedding_service = get_embedding_service()
        embeddings = await embedding_service.embed_batch([chunk.text for chunk in chunks])
        vector_store = VectorStore(
            persist_directory=str(settings.chroma_persist_dir),
            prefer_chroma=settings.vector_store == "chroma",
            collection_name=settings.chroma_collection,
        )
        vector_store.upsert(
            document_id=document_id,
            chunks=chunks,
            embeddings=embeddings,
            doc_meta={"filename": document["original_name"]},
        )
        with get_connection() as conn:
            ChunkRepo(conn).insert_many(document_id, chunks)
            DocumentRepo(conn).update_status(document_id, "READY", chunk_count=len(chunks))
    except Exception as exc:
        with get_connection() as conn:
            DocumentRepo(conn).update_status(document_id, "FAILED", error_message=str(exc))
