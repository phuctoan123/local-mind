# LocalMind Context Checkpoint

## Project Snapshot

LocalMind is a document Q&A application using Retrieval-Augmented Generation (RAG).
It supports uploading PDF, DOCX, and TXT files, parsing and chunking their content,
embedding chunks, storing vectors, retrieving relevant context, and answering
questions with source citations.

The project is structured as a FastAPI backend plus React/Vite frontend.

## High-Level Structure

```text
app/
  main.py                     FastAPI app setup, CORS, middleware, routers
  config.py                   .env loading, provider settings, active model helpers
  database.py                 SQLite connection helpers + migration runner
  dependencies.py             Provider factories for LLM, embedding, vector store

  api/
    collections.py           Create/list/delete collections, assign documents
    documents.py              Upload/list/get/delete documents, preview chunks
    chat.py                   Chat API, streaming SSE chat, sessions
    retrieval.py              Retrieval-only endpoint /api/v1/chunks
    openai_compat.py          Basic /v1/chat/completions endpoint
    research.py             Multi-step research/report endpoint
    health.py                 Health check for SQLite, vector store, providers

  ingestion/
    worker.py                 Document ingestion pipeline
    chunker.py                Recursive chunking with overlap
    parsers/                  PDF, DOCX, TXT parsers

  services/
    retrieval_engine.py       Hybrid/vector retrieval orchestration
    lexical_search.py         BM25 keyword search over SQLite chunks
    hybrid_retriever.py       Reciprocal Rank Fusion (RRF)
    vector_store.py           ChromaDB vector store + SQLite vector fallback
    rag_service.py            Builds prompt, runs retrieval + LLM generation
    research_service.py       Plans retrieval steps and synthesizes cited reports
    llm_client.py             Ollama chat client
    embedding_service.py      Ollama embedding client
    mistral_llm_client.py     Mistral/LeChat chat client
    mistral_embedding_service.py
    google_llm_client.py      Google AI Studio Gemini chat client
    google_embedding_service.py

  db/repositories/
    collection_repo.py        Collection CRUD, document assignment, ready doc IDs

ui/src/
  App.tsx                     Main layout and selected document state
  api/client.ts               REST/SSE client
  hooks/useChat.ts            Streaming chat state
  hooks/useCollections.ts     Collection list/create/delete/assignment state
  hooks/useDocuments.ts       Document list/upload/delete state
  components/                 Chat, collections, document list, upload, citations, badges
```

## Current Provider Logic

Provider switching is controlled by `.env`.

Important config values:

```env
LLM_PROVIDER=mistral|google|ollama
EMBEDDING_PROVIDER=mistral|google|ollama
CHROMA_COLLECTION=documents_mistral
RETRIEVAL_MODE=hybrid
```

Important helpers in `app/config.py`:

- `get_active_llm_model()`
- `get_active_embedding_model()`
- `ensure_data_dirs()`

Important factory functions in `app/dependencies.py`:

- `get_vector_store()`
- `get_embedding_service()`
- `get_llm_client()`
- `get_retrieval_engine()`

These choose Mistral, Google, or Ollama implementations based on `.env`.

## Database Migrations

`app/database.py` now owns a small SQLite migration runner.

Important objects:

- `MIGRATIONS`
- `run_migrations(conn)`
- `migration_status(conn)`
- `init_db(path=None)`

Applied versions are tracked in `schema_migrations`. App startup still calls
`init_db()`, so migrations run before API routes are served. `scripts/migrate_db.py`
can be used to run migrations explicitly, and `/api/v1/health` reports migration
status under the SQLite component.

## Current RAG Flow

### Upload

Endpoint: `POST /api/v1/upload`

Implemented in `app/api/documents.py`.

Flow:

1. Validate file extension and size.
2. Save raw file under `data/raw`.
3. Create SQLite document row with status `PENDING`.
4. Start background ingestion task.

### Ingestion

Function: `process_document(document_id)` in `app/ingestion/worker.py`.

Flow:

1. Load document metadata.
2. Set status `PROCESSING`.
3. Parse document through MIME-specific parser.
4. Validate that text was extracted.
5. Chunk parsed pages using `RecursiveChunker`.
6. Validate at least one chunk exists.
7. Embed chunks using active embedding provider.
8. Validate embedding count matches chunk count.
9. Upsert vectors into `VectorStore`.
10. Save chunks into SQLite.
11. Set status `READY`.
12. On failure, set status `FAILED` with `error_message`.

Important guard:

- Empty parse/chunk/embedding no longer marks document `READY`.

### Retrieval

Function: `RetrievalEngine.retrieve(...)` in `app/services/retrieval_engine.py`.

Current mode: Hybrid RAG.

Flow:

1. Embed query with active embedding provider.
2. If `RETRIEVAL_MODE=hybrid`:
   - vector search top `VECTOR_TOP_K`
   - BM25 search top `BM25_TOP_K`
   - merge with Reciprocal Rank Fusion using `RRF_K`
   - return final `top_k`
3. If vector/BM25 returns nothing, fallback to simple keyword retrieval.

Important files:

- `app/services/lexical_search.py`
  - `BM25Search.search(...)`
  - `tokenize(...)`
- `app/services/hybrid_retriever.py`
  - `reciprocal_rank_fusion(...)`
- `app/services/query_rewriter.py`
  - deterministic retrieval-facing query cleanup
- `app/services/reranker.py`
  - local lexical reranker over fused candidates
- `app/services/vector_store.py`
  - `VectorStore.query(...)`
  - `VectorStore.upsert(...)`
  - `VectorStore.health(...)`

Debug endpoint:

- `POST /api/v1/chunks/debug`
  - returns vector, BM25, fused, reranked, fallback, and final chunks

### Generation

Class: `RagService` in `app/services/rag_service.py`.

Important methods:

- `chat(request)`
- `stream_chat_events(request)`
- `build_prompt(...)`

Flow:

1. Retrieve chunks.
2. Build source citations.
3. Load session history if `session_id` exists.
4. Build prompt with context/history/question.
5. Call active LLM provider.
6. Validate answer citations against retrieved context.
7. Return answer + sources + citation validation + latency.

Streaming emits SSE-style events:

```text
sources
token
citation_validation
done
error
```

Streaming chat now preserves session history by opening DB connection inside
the streaming generator in `app/api/chat.py`.

## Vector Store Logic

Class: `VectorStore` in `app/services/vector_store.py`.

Primary backend:

- ChromaDB persistent client

Fallback:

- SQLite table `vectors`

Important behavior:

- Chroma init failure is no longer silent.
- `VectorStore.health()` reports:
  - `status`: `ok` or `degraded`
  - `backend`: actual backend
  - `configured_backend`
  - `collection`
  - `message`: init error if any

## Frontend Logic

### Document Selection

Implemented in:

- `ui/src/App.tsx`
- `ui/src/components/DocumentList.tsx`

Behavior:

- Only `READY` documents can be selected.
- User can select individual documents or use `All/Clear`.
- If no document is selected, chat searches all ready documents.
- Selected IDs are passed to `chat.ask(query, selectedReadyDocumentIds)`.

### Streaming Chat

Implemented in:

- `ui/src/api/client.ts`
  - `streamChat(...)`
- `ui/src/hooks/useChat.ts`
- `ui/src/components/ChatWindow.tsx`

Behavior:

- Adds user message and placeholder assistant message.
- Consumes SSE events.
- `sources` updates citations.
- `token` appends streamed text.
- `done` stores latency.
- `error` shows message.

### Answer Rendering

Assistant messages use `react-markdown`.
Source citations are expandable blocks showing filename, page, score, and preview.

## Important API Endpoints

```text
GET    /api/v1/collections
POST   /api/v1/collections
DELETE /api/v1/collections/{collection_id}
PUT    /api/v1/collections/{collection_id}/documents/{document_id}
DELETE /api/v1/collections/{collection_id}/documents/{document_id}
GET    /api/v1/collections/{collection_id}/ready-documents
POST   /api/v1/upload
GET    /api/v1/documents
GET    /api/v1/documents/{document_id}
GET    /api/v1/documents/{document_id}/chunks
DELETE /api/v1/documents/{document_id}
POST   /api/v1/chunks
POST   /api/v1/chunks/debug
POST   /api/v1/chat
POST   /api/v1/research
POST   /api/v1/sessions
DELETE /api/v1/sessions/{session_id}
GET    /api/v1/health
POST   /v1/chat/completions
```

## Recent Review Fixes Already Implemented

1. Streaming chat now preserves `session_id` and session history.
2. Ingestion no longer marks empty/failed parsing as `READY`.
3. Chroma fallback is visible through health status.
4. OpenAI-compatible endpoint no longer hard-codes Ollama metadata/errors.
5. Hybrid retrieval added: BM25 + vector search + RRF.
6. UI now supports selecting documents before chat.
7. Phase 1 retrieval quality started:
   - deterministic query rewriting
   - local lexical reranking
   - retrieval debug endpoint/UI panel
   - lightweight citation validation after generation
8. Phase 3 research assistant started:
   - `POST /api/v1/research`
   - deterministic multi-step query planning
   - evidence synthesis with citation validation
   - frontend Research assistant panel
9. Phase 2 document workspace started:
   - collections schema and API
   - document collection membership on document responses
   - frontend Collections panel
   - add/remove documents from the active collection
   - "Use ready documents" action to select collection docs for chat/research
10. Phase 4.1 database migration layer started:
   - `schema_migrations` table
   - versioned built-in SQLite migrations
   - `scripts/migrate_db.py`
   - health endpoint reports migration status

## Known Remaining Gaps

- Upload validation still mainly checks extension, not file signature/magic bytes.
- Reranker/query rewriting/citation validation are lightweight deterministic implementations,
  not LLM or cross-encoder quality yet.
- Migration runner is built in, but there is no Alembic integration yet.
- Test coverage is still mostly unit-level, not full integration.
- Frontend build could not be verified in sandbox because Node hits Windows permission errors.
- `scripts/view_data.py` exists as untracked local file and was not touched.

## Verification Commands Used

```powershell
python -m compileall app scripts tests
python -m pytest tests/unit -p no:cacheprovider
```

Current backend unit status during last check:

```text
20 passed
```

## Git/Security Notes

- `.env` is ignored and must not be committed.
- `.env.example` is safe and contains placeholders only.
- Runtime data is ignored:
  - `data/raw`
  - `data/sqlite`
  - `data/chroma`
- `node_modules`, `.venv`, `__pycache__`, and test cache are ignored.
