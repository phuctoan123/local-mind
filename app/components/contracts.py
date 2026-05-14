from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from app.ingestion.chunker import Chunk
from app.services.vector_store import RetrievedChunk


class EmbeddingComponent(Protocol):
    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text query."""

    async def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Embed a batch of text chunks."""


class LLMComponent(Protocol):
    async def generate(
        self,
        prompt: str,
        stream: bool = False,
        temperature: float = 0.1,
        top_p: float = 0.9,
        num_ctx: int = 4096,
        num_predict: int = 1024,
    ) -> str | AsyncIterator[str]:
        """Generate a text response."""


class VectorStoreComponent(Protocol):
    def upsert(
        self,
        document_id: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        doc_meta: dict,
    ) -> None:
        """Persist chunk embeddings."""

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        document_ids: list[str] | None = None,
        min_score: float = 0.0,
    ) -> list[RetrievedChunk]:
        """Retrieve relevant chunks."""

    def delete_by_document(self, document_id: str) -> int:
        """Delete vectors for a document."""
