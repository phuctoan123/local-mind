# Development

## Backend

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
python scripts/init_db.py
uvicorn app.main:app --reload
```

## Frontend

```bash
cd ui
npm install
npm run dev
```

## Tests

```bash
python -m pytest
```

Unit tests focus on pure logic that can run offline:

```bash
python -m pytest tests/unit
```

Integration tests exercise the FastAPI routes with a temporary SQLite database,
temporary raw/vector storage, a SQLite vector fallback, and fake LLM/embedding
providers. They do not require Ollama, Mistral, Google API keys, or ChromaDB:

```bash
python -m pytest tests/integration
```

Provider smoke scripts and manual end-to-end runs are still needed when changing
real Ollama, Mistral, Google, or ChromaDB behavior.

## Hybrid Retrieval

LocalMind can combine semantic vector search with BM25 keyword search:

```env
RETRIEVAL_MODE=hybrid
VECTOR_TOP_K=20
BM25_TOP_K=20
RRF_K=60
TOP_K=3
```

Set `RETRIEVAL_MODE=vector` to use vector-only retrieval. The UI can pass
`document_ids` by selecting ready documents in the sidebar.

## Google AI Studio Mode

Set these values in `.env`:

```env
LLM_PROVIDER=google
EMBEDDING_PROVIDER=google
GOOGLE_API_KEY=your_key_here
GOOGLE_MODEL=gemini-2.5-flash
GOOGLE_EMBED_MODEL=gemini-embedding-001
CHROMA_COLLECTION=documents_google
```

Then verify:

```bash
python scripts/check_google_ai.py
```

After switching embedding providers, delete and re-upload documents so vectors
are regenerated with the selected embedding model.

## Mistral / LeChat Mode

Set these values in `.env`:

```env
LLM_PROVIDER=mistral
EMBEDDING_PROVIDER=mistral
MISTRAL_API_KEY=your_key_here
MISTRAL_MODEL=mistral-small-latest
MISTRAL_EMBED_MODEL=mistral-embed
CHROMA_COLLECTION=documents_mistral
```

Then verify:

```bash
python scripts/check_mistral.py
```

After switching embedding providers, delete and re-upload documents so vectors
are regenerated with `mistral-embed`.
