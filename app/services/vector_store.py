from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

from app.database import get_connection, init_db
from app.ingestion.chunker import Chunk


@dataclass(frozen=True)
class RetrievedChunk:
    document_id: str
    filename: str
    page_number: int | None
    chunk_index: int
    text: str
    score: float
    char_start: int | None
    char_end: int | None


class VectorStore:
    def __init__(
        self,
        persist_directory: str,
        prefer_chroma: bool = True,
        collection_name: str = "documents",
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.configured_backend = "chroma" if prefer_chroma else "sqlite-vector"
        self.init_error: str | None = None
        self._chroma_collection = None
        if prefer_chroma:
            self._try_init_chroma()
        init_db()

    @property
    def backend_name(self) -> str:
        return "chroma" if self._chroma_collection is not None else "sqlite-vector"

    def _try_init_chroma(self) -> None:
        try:
            import chromadb

            client = chromadb.PersistentClient(path=self.persist_directory)
            self._chroma_collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:
            self.init_error = f"{type(exc).__name__}: {exc}"
            self._chroma_collection = None

    def upsert(
        self,
        document_id: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        doc_meta: dict[str, Any],
    ) -> None:
        ids = [f"{document_id}_{chunk.chunk_index}" for chunk in chunks]
        metadatas = [
            {
                "document_id": document_id,
                "filename": doc_meta["filename"],
                "page_number": chunk.source_page,
                "chunk_index": chunk.chunk_index,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
            }
            for chunk in chunks
        ]
        texts = [chunk.text for chunk in chunks]
        if self._chroma_collection is not None:
            self._chroma_collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            return
        with get_connection() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO vectors (id, document_id, chunk_index, text, embedding, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        ids[index],
                        document_id,
                        chunks[index].chunk_index,
                        chunks[index].text,
                        json.dumps(embeddings[index]),
                        json.dumps(metadatas[index]),
                    )
                    for index in range(len(chunks))
                ],
            )

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        document_ids: list[str] | None = None,
        min_score: float = 0.3,
    ) -> list[RetrievedChunk]:
        if self._chroma_collection is not None:
            where = {"document_id": {"$in": document_ids}} if document_ids else None
            result = self._chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
            chunks: list[RetrievedChunk] = []
            for text, metadata, distance in zip(
                result.get("documents", [[]])[0],
                result.get("metadatas", [[]])[0],
                result.get("distances", [[]])[0],
                strict=False,
            ):
                score = max(0.0, 1.0 - float(distance))
                if score >= min_score:
                    chunks.append(_retrieved_from_meta(text, metadata, score))
            return chunks
        return self._query_sqlite(query_embedding, top_k, document_ids, min_score)

    def _query_sqlite(
        self,
        query_embedding: list[float],
        top_k: int,
        document_ids: list[str] | None,
        min_score: float,
    ) -> list[RetrievedChunk]:
        where = ""
        params: list[Any] = []
        if document_ids:
            placeholders = ",".join("?" for _ in document_ids)
            where = f"WHERE document_id IN ({placeholders})"
            params.extend(document_ids)
        with get_connection() as conn:
            rows = conn.execute(f"SELECT * FROM vectors {where}", params).fetchall()
        scored: list[RetrievedChunk] = []
        for row in rows:
            embedding = json.loads(row["embedding"])
            score = cosine_similarity(query_embedding, embedding)
            if score >= min_score:
                scored.append(_retrieved_from_meta(row["text"], json.loads(row["metadata"]), score))
        return sorted(scored, key=lambda chunk: chunk.score, reverse=True)[:top_k]

    def delete_by_document(self, document_id: str) -> int:
        count = 0
        if self._chroma_collection is not None:
            existing = self._chroma_collection.get(where={"document_id": document_id})
            count = len(existing.get("ids", []))
            if count:
                self._chroma_collection.delete(where={"document_id": document_id})
        with get_connection() as conn:
            if not count:
                count = conn.execute(
                    "SELECT COUNT(*) FROM vectors WHERE document_id = ?",
                    (document_id,),
                ).fetchone()[0]
            conn.execute("DELETE FROM vectors WHERE document_id = ?", (document_id,))
        return count

    def health(self) -> dict[str, Any]:
        with get_connection() as conn:
            chunk_count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        return {
            "status": "degraded" if self.init_error else "ok",
            "backend": self.backend_name,
            "configured_backend": self.configured_backend,
            "collection": self.collection_name,
            "message": self.init_error,
            "document_count": doc_count,
            "chunk_count": chunk_count,
        }


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _retrieved_from_meta(text: str, metadata: dict[str, Any], score: float) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=str(metadata["document_id"]),
        filename=str(metadata["filename"]),
        page_number=metadata.get("page_number"),
        chunk_index=int(metadata["chunk_index"]),
        text=text,
        score=score,
        char_start=metadata.get("char_start"),
        char_end=metadata.get("char_end"),
    )
