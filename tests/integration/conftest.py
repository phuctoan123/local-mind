from __future__ import annotations

import importlib
import shutil
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import get_connection, init_db
from app.db.repositories.chunk_repo import ChunkRepo
from app.db.repositories.document_repo import DocumentRepo
from app.ingestion.chunker import RecursiveChunker
from app.ingestion.parsers.base import ParsedPage
from app.services.retrieval_engine import RetrievalEngine
from app.services.vector_store import VectorStore
from app.utils.file_utils import detect_mime_type, secure_filename


@dataclass
class IntegrationHarness:
    client: TestClient
    data_dir: Path
    raw_files_dir: Path
    sqlite_path: Path
    vector_store: VectorStore
    embedding_service: FakeEmbeddingService

    def seed_document(
        self,
        filename: str = "contract.txt",
        text: str = "Contract termination requires thirty days notice and manager approval.",
        status: str = "READY",
    ) -> dict[str, Any]:
        document_id = str(uuid.uuid4())
        safe_name = secure_filename(filename)
        suffix = Path(safe_name).suffix.lower() or ".txt"
        stored_name = f"{document_id}{suffix}"
        file_path = self.raw_files_dir / stored_name
        file_path.write_bytes(text.encode("utf-8"))
        doc = {
            "id": document_id,
            "filename": stored_name,
            "original_name": safe_name,
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size,
            "mime_type": detect_mime_type(safe_name),
            "status": "PENDING",
        }
        with get_connection() as conn:
            DocumentRepo(conn).create(doc)

        if status == "READY":
            chunks = RecursiveChunker(chunk_size=128, chunk_overlap=8, min_chunk_length=5).chunk(
                [ParsedPage(page_number=1, text=text, metadata={})]
            )
            embeddings = [self.embedding_service.embedding_for(chunk.text) for chunk in chunks]
            self.vector_store.upsert(
                document_id,
                chunks,
                embeddings,
                doc_meta={"filename": safe_name},
            )
            with get_connection() as conn:
                ChunkRepo(conn).insert_many(document_id, chunks)
                DocumentRepo(conn).update_status(document_id, "READY", chunk_count=len(chunks))
        elif status != "PENDING":
            with get_connection() as conn:
                DocumentRepo(conn).update_status(document_id, status)

        with get_connection() as conn:
            return DocumentRepo(conn).get(document_id)

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        with get_connection() as conn:
            return DocumentRepo(conn).get(document_id)

    def message_count(self, session_id: str) -> int:
        with get_connection() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id = ?",
                (session_id,),
            ).fetchone()[0]


class FakeEmbeddingService:
    terms = (
        "contract",
        "termination",
        "notice",
        "invoice",
        "payment",
        "security",
        "policy",
        "research",
        "risk",
    )

    def embedding_for(self, text: str) -> list[float]:
        lowered = text.lower()
        return [float(lowered.count(term)) + 0.1 for term in self.terms]

    async def embed_text(self, text: str) -> list[float]:
        return self.embedding_for(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embedding_for(text) for text in texts]

    async def health(self) -> dict[str, str]:
        return {"status": "ok", "model": "fake-embedding"}


class FakeLLMClient:
    answer = "According to contract.txt, Page 1, termination requires thirty days notice."

    async def generate(self, prompt: str, stream: bool = False, **_: Any):
        if stream:
            return self._stream_answer()
        return self.answer

    async def _stream_answer(self):
        for token in ("According to contract.txt, ", "Page 1, ", "termination requires notice."):
            yield token

    async def health(self) -> dict[str, str]:
        return {"status": "ok", "model": "fake-llm"}


@pytest.fixture
def integration():
    original_settings = {
        "data_dir": settings.data_dir,
        "raw_files_dir": settings.raw_files_dir,
        "chroma_persist_dir": settings.chroma_persist_dir,
        "sqlite_path": settings.sqlite_path,
        "vector_store": settings.vector_store,
        "chroma_collection": settings.chroma_collection,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "min_chunk_length": settings.min_chunk_length,
        "retrieval_mode": settings.retrieval_mode,
        "vector_top_k": settings.vector_top_k,
        "bm25_top_k": settings.bm25_top_k,
        "rrf_k": settings.rrf_k,
        "enable_query_rewriting": settings.enable_query_rewriting,
        "enable_reranking": settings.enable_reranking,
        "rerank_candidate_k": settings.rerank_candidate_k,
        "enable_citation_validation": settings.enable_citation_validation,
        "min_similarity_score": settings.min_similarity_score,
        "max_upload_size_mb": settings.max_upload_size_mb,
        "max_docx_zip_entries": settings.max_docx_zip_entries,
        "max_docx_uncompressed_mb": settings.max_docx_uncompressed_mb,
        "max_docx_compression_ratio": settings.max_docx_compression_ratio,
        "cors_origins": settings.cors_origins,
        "api_key": settings.api_key,
    }
    test_root = Path(__file__).resolve().parents[2] / ".pytest_tmp" / uuid.uuid4().hex
    data_dir = test_root / "data"
    raw_files_dir = data_dir / "raw"
    sqlite_path = data_dir / "sqlite" / "app.db"
    chroma_dir = data_dir / "chroma"
    overrides = {
        "data_dir": data_dir,
        "raw_files_dir": raw_files_dir,
        "chroma_persist_dir": chroma_dir,
        "sqlite_path": sqlite_path,
        "vector_store": "sqlite-vector",
        "chroma_collection": f"test_{uuid.uuid4().hex}",
        "chunk_size": 128,
        "chunk_overlap": 8,
        "min_chunk_length": 5,
        "retrieval_mode": "hybrid",
        "vector_top_k": 10,
        "bm25_top_k": 10,
        "rrf_k": 60,
        "enable_query_rewriting": True,
        "enable_reranking": True,
        "rerank_candidate_k": 6,
        "enable_citation_validation": True,
        "min_similarity_score": 0.0,
        "max_upload_size_mb": 1,
        "max_docx_zip_entries": 500,
        "max_docx_uncompressed_mb": 100,
        "max_docx_compression_ratio": 100,
        "cors_origins": ("http://localhost:3000",),
        "api_key": "",
    }
    for name, value in overrides.items():
        object.__setattr__(settings, name, value)

    init_db(sqlite_path)
    embedding_service = FakeEmbeddingService()
    llm_client = FakeLLMClient()
    vector_store = VectorStore(
        persist_directory=str(chroma_dir),
        prefer_chroma=False,
        collection_name=settings.chroma_collection,
    )
    retrieval_engine = RetrievalEngine(vector_store, embedding_service)

    if "app.main" in sys.modules:
        main_module = importlib.reload(sys.modules["app.main"])
    else:
        main_module = importlib.import_module("app.main")
    app = main_module.create_app()

    from app import dependencies
    from app.api import chat, documents, health, research, retrieval
    from app.ingestion import worker

    dependencies.get_embedding_service.cache_clear()
    dependencies.get_vector_store.cache_clear()
    dependencies.get_llm_client.cache_clear()

    def get_test_retrieval_engine():
        return retrieval_engine

    def get_test_vector_store():
        return vector_store

    patcher = pytest.MonkeyPatch()
    patcher.setattr(worker, "get_embedding_service", lambda: embedding_service)
    patcher.setattr(chat, "get_retrieval_engine", get_test_retrieval_engine)
    patcher.setattr(chat, "get_llm_client", lambda: llm_client)
    patcher.setattr(retrieval, "get_retrieval_engine", get_test_retrieval_engine)
    patcher.setattr(research, "get_retrieval_engine", get_test_retrieval_engine)
    patcher.setattr(research, "get_llm_client", lambda: llm_client)
    patcher.setattr(health, "get_vector_store", get_test_vector_store)
    patcher.setattr(health, "get_embedding_service", lambda: embedding_service)
    patcher.setattr(health, "get_llm_client", lambda: llm_client)
    patcher.setattr(documents, "get_vector_store", get_test_vector_store)

    with TestClient(app) as client:
        harness = IntegrationHarness(
            client=client,
            data_dir=data_dir,
            raw_files_dir=raw_files_dir,
            sqlite_path=sqlite_path,
            vector_store=vector_store,
            embedding_service=embedding_service,
        )
        try:
            yield harness
        finally:
            patcher.undo()
            dependencies.get_embedding_service.cache_clear()
            dependencies.get_vector_store.cache_clear()
            dependencies.get_llm_client.cache_clear()
            for name, value in original_settings.items():
                object.__setattr__(settings, name, value)
            shutil.rmtree(test_root, ignore_errors=True)
