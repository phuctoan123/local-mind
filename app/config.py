from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value.lower() in {"1", "true", "yes", "on"}


_load_dotenv(Path(".env"))


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "ollama")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "mistral:7b")
    ollama_embed_model: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    ollama_timeout: int = int(os.getenv("OLLAMA_TIMEOUT", "600"))
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    google_base_url: str = os.getenv(
        "GOOGLE_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta",
    )
    google_model: str = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
    google_embed_model: str = os.getenv("GOOGLE_EMBED_MODEL", "gemini-embedding-001")
    google_timeout: int = int(os.getenv("GOOGLE_TIMEOUT", "120"))
    mistral_api_key: str = os.getenv("MISTRAL_API_KEY", "")
    mistral_base_url: str = os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")
    mistral_model: str = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
    mistral_embed_model: str = os.getenv("MISTRAL_EMBED_MODEL", "mistral-embed")
    mistral_timeout: int = int(os.getenv("MISTRAL_TIMEOUT", "120"))
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    llm_top_p: float = float(os.getenv("LLM_TOP_P", "0.9"))
    llm_num_ctx: int = int(os.getenv("LLM_NUM_CTX", "2048"))
    llm_num_predict: int = int(os.getenv("LLM_NUM_PREDICT", "256"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "512"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "64"))
    min_chunk_length: int = int(os.getenv("MIN_CHUNK_LENGTH", "50"))
    retrieval_mode: str = os.getenv("RETRIEVAL_MODE", "hybrid")
    top_k: int = int(os.getenv("TOP_K", "3"))
    min_similarity_score: float = float(os.getenv("MIN_SIMILARITY_SCORE", "0.15"))
    max_context_tokens: int = int(os.getenv("MAX_CONTEXT_TOKENS", "1200"))
    vector_top_k: int = int(os.getenv("VECTOR_TOP_K", "20"))
    bm25_top_k: int = int(os.getenv("BM25_TOP_K", "20"))
    rrf_k: int = int(os.getenv("RRF_K", "60"))
    enable_query_rewriting: bool = _bool(os.getenv("ENABLE_QUERY_REWRITING", "true"))
    enable_reranking: bool = _bool(os.getenv("ENABLE_RERANKING", "true"))
    rerank_candidate_k: int = int(os.getenv("RERANK_CANDIDATE_K", "12"))
    enable_citation_validation: bool = _bool(os.getenv("ENABLE_CITATION_VALIDATION", "true"))
    data_dir: Path = Path(os.getenv("DATA_DIR", "./data"))
    raw_files_dir: Path = Path(os.getenv("RAW_FILES_DIR", "./data/raw"))
    chroma_persist_dir: Path = Path(os.getenv("CHROMA_PERSIST_DIR", "./data/chroma"))
    sqlite_path: Path = Path(os.getenv("SQLITE_PATH", "./data/sqlite/app.db"))
    vector_store: str = os.getenv("VECTOR_STORE", "chroma")
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "documents")
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
        if origin.strip()
    )
    api_key: str = os.getenv("API_KEY", "")
    max_upload_size_mb: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    allowed_extensions: tuple[str, ...] = tuple(
        ext.strip().lower()
        for ext in os.getenv("ALLOWED_EXTENSIONS", "pdf,txt,docx").split(",")
        if ext.strip()
    )
    session_ttl_minutes: int = int(os.getenv("SESSION_TTL_MINUTES", "30"))
    max_history_turns: int = int(os.getenv("MAX_HISTORY_TURNS", "10"))
    enable_ocr: bool = _bool(os.getenv("ENABLE_OCR", "false"))
    enable_streaming: bool = _bool(os.getenv("ENABLE_STREAMING", "true"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()


def get_active_llm_model() -> str:
    provider = settings.llm_provider.lower()
    if provider == "google":
        return settings.google_model
    if provider == "mistral":
        return settings.mistral_model
    return settings.ollama_model


def get_active_embedding_model() -> str:
    provider = settings.embedding_provider.lower()
    if provider == "google":
        return settings.google_embed_model
    if provider == "mistral":
        return settings.mistral_embed_model
    return settings.ollama_embed_model


def ensure_data_dirs() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.raw_files_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
