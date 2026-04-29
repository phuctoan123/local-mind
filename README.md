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

## Frontend Setup

```bash
cd ui
npm install
npm run dev
```

The UI runs at [http://localhost:3000](http://localhost:3000).

## Core API

- `POST /api/v1/upload` uploads and enqueues a document for ingestion
- `GET /api/v1/documents` lists indexed documents
- `GET /api/v1/documents/{document_id}` fetches document metadata
- `GET /api/v1/documents/{document_id}/chunks` previews parsed chunks
- `DELETE /api/v1/documents/{document_id}` removes a document, chunks, vectors, and raw file
- `POST /api/v1/chunks` retrieves relevant source chunks
- `POST /api/v1/chat` asks a question against indexed documents
- `POST /api/v1/sessions` creates a chat session
- `DELETE /api/v1/sessions/{session_id}` deletes a chat session
- `GET /api/v1/health` checks configured providers and storage
- `POST /v1/chat/completions` provides a basic OpenAI-compatible chat endpoint

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
