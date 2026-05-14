# LocalMind

LocalMind is a privacy-focused document Q&A app. It lets you upload PDF, TXT,
and DOCX files, index them locally, and ask questions with source citations
through a retrieval-augmented generation pipeline.

## What Is Included

- FastAPI backend with `/api/v1` endpoints
- SQLite metadata storage
- Document parsers for PDF, TXT, and DOCX
- Recursive chunking with overlap
- Swappable model providers: Ollama, Google AI Studio, and Mistral
- Swappable embedding providers: Ollama, Google AI Studio, and Mistral
- ChromaDB vector store when installed, with a SQLite vector fallback for development
- React + Vite UI for document upload, document list, streaming chat, and source citations

## Prerequisites

- Python 3.11+
- Node.js 16.20+ for the pinned Vite 4 frontend
- One configured model provider:
  - Ollama for fully local mode
  - Mistral API for hosted LeChat/Mistral mode
  - Google AI Studio for Gemini mode

## Backend Setup

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python scripts/init_db.py
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API docs are available at [http://localhost:8000/docs](http://localhost:8000/docs).

`init_db.py` runs the SQLite migration runner. You can also run migrations
explicitly:

```bash
python scripts/migrate_db.py
```

## Frontend Setup

```bash
cd ui
npm install
npm run dev
```

The UI runs at [http://localhost:3000](http://localhost:3000).

## Core API

- `POST /api/v1/upload` uploads and enqueues a document for ingestion
- `GET /api/v1/collections` lists document collections
- `POST /api/v1/collections` creates a collection
- `DELETE /api/v1/collections/{collection_id}` deletes a collection
- `PUT /api/v1/collections/{collection_id}/documents/{document_id}` adds a document
- `DELETE /api/v1/collections/{collection_id}/documents/{document_id}` removes a document
- `GET /api/v1/documents` lists indexed documents
- `GET /api/v1/documents/{document_id}` fetches document metadata
- `GET /api/v1/documents/{document_id}/chunks` previews parsed chunks
- `DELETE /api/v1/documents/{document_id}` removes a document, chunks, vectors, and raw file
- `POST /api/v1/chunks` retrieves relevant source chunks
- `POST /api/v1/chunks/debug` returns retrieval stages for debugging
- `POST /api/v1/chat` asks a question against indexed documents
- `POST /api/v1/research` runs multi-step retrieval and synthesizes a cited report
- `POST /api/v1/sessions` creates a chat session
- `DELETE /api/v1/sessions/{session_id}` deletes a chat session
- `GET /api/v1/health` checks configured providers and storage
- `POST /v1/chat/completions` provides a basic OpenAI-compatible chat endpoint

## Retrieval

LocalMind supports hybrid retrieval with vector search plus BM25 keyword search
merged by Reciprocal Rank Fusion (RRF). A lightweight query rewrite pass removes
common prompt filler before retrieval, and a local lexical reranker reorders the
merged candidates before context is sent to the LLM:

```env
RETRIEVAL_MODE=hybrid
VECTOR_TOP_K=20
BM25_TOP_K=20
RRF_K=60
ENABLE_QUERY_REWRITING=true
ENABLE_RERANKING=true
RERANK_CANDIDATE_K=12
ENABLE_CITATION_VALIDATION=true
TOP_K=3
```

Use `POST /api/v1/chunks/debug` with the same body as `/api/v1/chunks` to inspect
the vector, BM25, fused, reranked, fallback, and final returned chunks.
Chat responses also include a lightweight citation validation result that checks
answer overlap against retrieved context and whether the answer explicitly cites
source documents or pages.

## Research Mode

Use `POST /api/v1/research` for broader questions such as comparisons, risk
reviews, or report-style answers. LocalMind creates a few retrieval subqueries,
retrieves evidence for each step, asks the active LLM to synthesize a concise
research answer, and returns the research steps, sources, and citation validation.
The frontend includes a Research assistant panel above chat for this workflow.

## Collections

Collections let you organize documents into lightweight workspace groups. The UI
includes a Collections panel for creating collections, adding/removing documents,
and selecting all ready documents in a collection for chat, retrieval debug, or
research mode. Document list responses include `collection_ids` for each file.

## Database Migrations

LocalMind uses a small built-in SQLite migration runner. Applied migrations are
tracked in the `schema_migrations` table, and app startup calls `init_db()` so a
local database is upgraded before API routes are served. `/api/v1/health`
includes migration status under the SQLite component.

The UI also lets users select specific ready documents before asking a question.
When no document is selected, chat searches across all ready documents.

## Provider Modes

Fully local Ollama mode:

```env
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=phi3:mini
OLLAMA_EMBED_MODEL=nomic-embed-text:latest
CHROMA_COLLECTION=documents_ollama
```

Mistral mode:

```env
LLM_PROVIDER=mistral
EMBEDDING_PROVIDER=mistral
MISTRAL_API_KEY=your_key_here
MISTRAL_MODEL=mistral-small-latest
MISTRAL_EMBED_MODEL=mistral-embed
CHROMA_COLLECTION=documents_mistral
```

Google AI Studio mode:

```env
LLM_PROVIDER=google
EMBEDDING_PROVIDER=google
GOOGLE_API_KEY=your_key_here
GOOGLE_MODEL=gemini-2.5-flash
GOOGLE_EMBED_MODEL=gemini-embedding-001
CHROMA_COLLECTION=documents_google
```

After switching embedding providers, re-upload documents so vectors are regenerated
with the selected embedding model.

## Security Notes

- Do not commit `.env`.
- Runtime files under `data/` are ignored by Git.
- API keys should be stored only in local environment files or deployment secrets.
