from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.google_embedding_service import GoogleEmbeddingService
from app.services.google_llm_client import GoogleLLMClient
from app.services.llm_client import OllamaClient
from app.services.mistral_embedding_service import MistralEmbeddingService
from app.services.mistral_llm_client import MistralLLMClient
from app.services.retrieval_engine import RetrievalEngine
from app.services.vector_store import VectorStore


@lru_cache
def get_vector_store() -> VectorStore:
    return VectorStore(
        persist_directory=str(settings.chroma_persist_dir),
        prefer_chroma=settings.vector_store == "chroma",
        collection_name=settings.chroma_collection,
    )


@lru_cache
def get_embedding_service() -> EmbeddingService:
    if settings.embedding_provider.lower() == "google":
        return GoogleEmbeddingService(
            api_key=settings.google_api_key,
            model=settings.google_embed_model,
            base_url=settings.google_base_url,
            timeout=settings.google_timeout,
        )
    if settings.embedding_provider.lower() == "mistral":
        return MistralEmbeddingService(
            api_key=settings.mistral_api_key,
            model=settings.mistral_embed_model,
            base_url=settings.mistral_base_url,
            timeout=settings.mistral_timeout,
        )
    return EmbeddingService(
        model=settings.ollama_embed_model,
        base_url=settings.ollama_base_url,
        timeout=settings.ollama_timeout,
    )


@lru_cache
def get_llm_client() -> OllamaClient:
    if settings.llm_provider.lower() == "google":
        return GoogleLLMClient(
            api_key=settings.google_api_key,
            model=settings.google_model,
            base_url=settings.google_base_url,
            timeout=settings.google_timeout,
        )
    if settings.llm_provider.lower() == "mistral":
        return MistralLLMClient(
            api_key=settings.mistral_api_key,
            model=settings.mistral_model,
            base_url=settings.mistral_base_url,
            timeout=settings.mistral_timeout,
        )
    return OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout=settings.ollama_timeout,
    )


def get_retrieval_engine() -> RetrievalEngine:
    return RetrievalEngine(get_vector_store(), get_embedding_service())
