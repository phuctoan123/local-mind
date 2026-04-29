# Architecture

LocalMind is a modular document Q&A system for retrieval-augmented generation.

## Backend

- `app/api` exposes FastAPI routers under `/api/v1`
- `app/ingestion` parses and chunks documents, then creates embeddings
- `app/services` contains Ollama, vector store, retrieval, and RAG orchestration
- `app/db/repositories` wraps SQLite metadata and session operations

## Data Flow

1. A user uploads a PDF, TXT, or DOCX file.
2. The backend validates size/type, stores the raw file, and creates a `PENDING` document row.
3. A background task parses text, chunks it, embeds chunks through Ollama, and upserts vectors.
4. A chat request embeds the query, retrieves matching chunks, builds a strict grounded prompt, and asks Ollama for the final answer.
5. The response includes source snippets and similarity scores.
