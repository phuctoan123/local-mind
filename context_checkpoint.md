  # LocalMind - Project Context

File nay la checkpoint context chinh cho project LocalMind. Dung no de tiep tuc ho tro
du an trong cac thread sau ma khong can hoi lai tu dau.

## Muc Tieu Du An

LocalMind la ung dung hoi dap tai lieu rieng tu theo mo hinh Retrieval-Augmented
Generation (RAG). Nguoi dung co the upload PDF, TXT, DOCX, de he thong parse noi
dung, chunk van ban, tao embedding, luu vector, truy xuat ngu canh lien quan va tra
loi cau hoi kem trich dan nguon.

Huong san pham:

- Chay tot o local/development, uu tien quyen rieng tu va kha nang dung model local.
- Van co the doi sang provider hosted nhu Mistral hoac Google AI Studio qua `.env`.
- UI tap trung vao workflow that: upload tai lieu, quan ly collection, chon tai lieu,
  hoi dap streaming, debug retrieval, va research/report co citation.

## Tech Stack / Framework

Backend:

- Python 3.11+.
- FastAPI cho HTTP API va SSE streaming.
- SQLite cho metadata, sessions, chunks, collections, migrations va vector fallback.
- ChromaDB persistent client la vector store mac dinh khi kha dung.
- Provider LLM/embedding co the thay doi:
  - Ollama cho che do local.
  - Mistral API.
  - Google AI Studio / Gemini.
- Pytest cho unit tests.
- Ruff config trong `pyproject.toml`, line length 100, target Python 3.11.

Frontend:

- React 18.
- TypeScript.
- Vite 4.
- `lucide-react` cho icons.
- `react-markdown` cho render cau tra loi assistant.

Scripts/dev:

- `python scripts/init_db.py` khoi tao DB va chay migrations.
- `python scripts/migrate_db.py` chay migration runner truc tiep.
- `python -m pytest` chay backend tests.
- `npm run build` trong `ui/` build frontend.

## Cau Truc Repo Chinh

```text
app/
  main.py                       FastAPI app setup, CORS, middleware, routers
  config.py                     Settings tu .env, provider config, helper model active
  database.py                   SQLite connection, schema, migration runner
  dependencies.py               Factory cho vector store, embedding, LLM, retrieval engine

  api/
    chat.py                     Chat API, streaming SSE, sessions
    collections.py              Collection CRUD va gan document vao collection
    documents.py                Upload/list/get/delete documents, preview chunks
    health.py                   Health check SQLite, migrations, vector store, providers
    openai_compat.py            Basic /v1/chat/completions compatibility
    research.py                 Multi-step research/report endpoint
    retrieval.py                Retrieval-only va retrieval debug endpoints

  db/repositories/
    chunk_repo.py               CRUD/query chunks
    collection_repo.py          Collection CRUD, membership, ready document IDs
    document_repo.py            Document metadata CRUD
    session_repo.py             Chat session/history CRUD

  ingestion/
    worker.py                   Pipeline ingestion background
    chunker.py                  Recursive chunker with overlap
    parsers/                    PDF, DOCX, TXT parsers

  models/
    chat.py                     Chat/session request-response models
    collection.py               Collection models
    document.py                 Document models
    health.py                   Health models
    openai.py                   OpenAI-compatible models
    research.py                 Research models
    retrieval.py                Retrieval/chunk/debug models

  services/
    citation_validator.py       Lightweight answer/source citation validation
    embedding_service.py        Ollama embedding client
    google_embedding_service.py Google embedding client
    google_llm_client.py        Google/Gemini chat client
    hybrid_retriever.py         Reciprocal Rank Fusion
    lexical_search.py           BM25 keyword retrieval over SQLite chunks
    llm_client.py               Ollama chat client
    mistral_embedding_service.py
    mistral_llm_client.py
    query_rewriter.py           Deterministic retrieval query cleanup
    rag_service.py              Retrieval + prompt + LLM answer flow
    reranker.py                 Local lexical reranker
    research_service.py         Multi-step research planning and synthesis
    retrieval_engine.py         Hybrid/vector retrieval orchestration
    vector_store.py             ChromaDB store plus SQLite vector fallback

ui/src/
  App.tsx                       Main UI layout, selected document state
  api/client.ts                 REST/SSE API client
  hooks/useChat.ts              Streaming chat state
  hooks/useCollections.ts       Collections state/actions
  hooks/useDocuments.ts         Documents/upload/delete state
  components/                   Chat, upload, documents, collections, research/debug panels

docs/
  api.md
  architecture.md
  development.md

scripts/
  check_google_ai.py
  check_mistral.py
  check_ollama.py
  init_db.py
  migrate_db.py
  view_data.py

tests/unit/
  Unit tests cho chunker, prompt builder, vector store, retrieval, reranker,
  query rewriter, citation validator, collections, research service, migrations.

data/
  raw/.gitkeep
  sqlite/.gitkeep
  chroma/.gitkeep
```

## Nhung Gi Da Hoan Thanh

Core RAG:

- Upload document qua `POST /api/v1/upload`.
- Upload validation da kiem tra extension, size va file signature/magic bytes cho
  PDF/DOCX/TXT truoc khi ghi file xuong disk.
- Parse PDF/TXT/DOCX.
- Recursive chunking voi overlap.
- Embedding chunks qua provider active.
- Luu metadata/chunks trong SQLite.
- Luu vectors trong ChromaDB, fallback SQLite neu Chroma bi loi.
- Retrieval context va chat voi source citations.
- Streaming chat qua SSE.

Provider switching:

- Ho tro Ollama, Mistral, Google cho LLM.
- Ho tro Ollama, Mistral, Google cho embedding.
- `.env.example` co cac config mau.
- `app/config.py` co `get_active_llm_model()` va `get_active_embedding_model()`.
- `app/dependencies.py` chon implementation theo `LLM_PROVIDER` va `EMBEDDING_PROVIDER`.

Retrieval quality:

- Hybrid retrieval mac dinh: vector search + BM25 + Reciprocal Rank Fusion.
- Deterministic query rewriting.
- Local lexical reranking.
- Fallback keyword retrieval khi vector/BM25 khong co ket qua.
- Endpoint debug: `POST /api/v1/chunks/debug`.
- UI debug panel cho retrieval stages.

Citation/research:

- Lightweight citation validation sau generation.
- Research endpoint: `POST /api/v1/research`.
- Research service tao nhieu retrieval steps, tong hop cau tra loi/report, tra ve sources
  va citation validation.
- UI Research assistant panel.

Collections/workspace:

- Schema va API collections.
- Gan/bo document khoi collection.
- Document response co `collection_ids`.
- UI Collections panel.
- Action "Use ready documents" de chon tat ca document ready trong collection cho chat,
  retrieval debug hoac research.

Database/migrations:

- Built-in SQLite migration runner trong `app/database.py`.
- Bang `schema_migrations`.
- App startup goi `init_db()` de chay migrations truoc khi serve API.
- `scripts/migrate_db.py`.
- `/api/v1/health` report migration status.

Review fixes da xu ly:

- Streaming chat giu dung `session_id` va session history.
- Ingestion khong danh dau `READY` neu parse/chunk/embedding rong hoac fail.
- Chroma fallback khong con silent; health endpoint bao `ok/degraded`, backend va error.
- OpenAI-compatible endpoint khong hard-code Ollama metadata/errors.
- UI cho phep chon document truoc khi chat; neu khong chon thi search tat ca ready docs.

Git/trang thai gan nhat:

- Branch: `main`.
- Remote: `origin` -> `https://github.com/phuctoan123/local-mind.git`.
- Commit da push gan nhat: `06ffdc9 Add hybrid retrieval and research workflows`.
- Sau lan push gan nhat, repo sach va `main` dong bo voi `origin/main`.

Verification gan nhat:

- `python -m pytest`: 43 passed sau khi them integration tests.
- `python -m pytest tests/integration`: 15 passed.
- `npm run build` trong `ui/`: pass sau khi chay ngoai sandbox do Node bi EPERM trong
  sandbox khi `lstat C:\Users\Toan`.
- `git diff --check`: khong co whitespace error; co warning LF se duoc Windows doi sang
  CRLF khi Git cham file.

## Nhung Issue / Bug / Task Dang Lam

Backlog/known gaps:

- Upload validation da co signature check co ban; van co the can hardening nang cao hon
  neu deploy public, vi TXT detection va DOCX structural checks chi o muc pragmatic.
- Query rewriting, reranker va citation validation dang la deterministic lightweight;
  co the nang cap bang LLM/cross-encoder neu can chat luong cao hon.
- Migration runner da co, nhung chua dung Alembic.
- Da co integration/API tests dau tien cho upload, ingestion, retrieval, chat streaming,
  research, collections va health; van can them frontend tests/manual browser QA.
- Can QA frontend bang browser cho cac UI moi: Collections, Retrieval Debug, Research,
  citation validation badge, document selection.
- Can review `scripts/view_data.py` neu muon giu nhu tool chinh thuc hay tach ra dev-only.
- Chua co auth phuc tap; middleware/API key config co trong project nhung can review neu
  deploy that.

Task uu tien tiep theo duoc suy luan:

- QA UI bang browser local.
- Cai thien citation quality va UI display cho research/chat.
- Lam ro migration strategy dai han neu schema tiep tuc phinh ra.

## File Hoac Module Quan Trong

- `app/config.py`: tat ca setting va env defaults.
- `app/dependencies.py`: factory layer; dung de them/sua provider ma khong rải logic
  provider trong routers.
- `app/database.py`: SQLite schema, migration runner, init DB.
- `app/main.py`: dang ky router va startup behavior.
- `app/ingestion/worker.py`: pipeline ingestion, validation trang thai document.
- `app/services/retrieval_engine.py`: orchestration retrieval chinh.
- `app/services/vector_store.py`: ChromaDB + SQLite vector fallback.
- `app/services/rag_service.py`: chat flow, prompt building, streaming, citation validation.
- `app/services/research_service.py`: research planning va synthesis.
- `app/services/lexical_search.py`: BM25 keyword search.
- `app/services/hybrid_retriever.py`: RRF merge.
- `app/services/reranker.py`: lexical reranker.
- `app/services/citation_validator.py`: answer/source validation.
- `app/api/*.py`: HTTP behavior va response contracts.
- `app/db/repositories/*.py`: DB access boundaries.
- `ui/src/api/client.ts`: frontend API/SSE contract.
- `ui/src/App.tsx`: global UI state, selected documents, panel composition.
- `ui/src/hooks/useChat.ts`: streaming chat state.
- `ui/src/hooks/useCollections.ts`: collection state/actions.
- `ui/src/components/DocumentList.tsx`: document selection va collection assignment entry.
- `ui/src/components/CollectionPanel.tsx`: collection workflow.
- `ui/src/components/ResearchPanel.tsx`: research workflow.
- `ui/src/components/RetrievalDebugPanel.tsx`: retrieval debug workflow.
- `.env.example`: documented configuration surface.
- `README.md`: setup va API overview.

## Coding Style / Convention Can Giu

Python/backend:

- Uu tien type hints va code ro rang.
- Config di qua `Settings` trong `app/config.py`.
- Provider-specific logic nam trong service/client rieng va factory trong `dependencies.py`.
- Routers trong `app/api/` nen mong, goi repositories/services thay vi nhồi business logic.
- DB access nen di qua repositories khi co boundary ro.
- Migration thay doi schema nen them vao `MIGRATIONS` trong `app/database.py`.
- Khong silent fallback cho loi quan trong; health endpoint nen expose trang thai degraded.
- Tests nen dat trong `tests/unit/`, dat ten theo module/behavior.
- Ruff line length 100; imports nen giu gon va sap xep sach.

Frontend:

- React function components + hooks.
- TypeScript types trong `ui/src/api/client.ts` can dong bo voi backend response models.
- API calls nen tap trung trong client/hook, component giu logic UI.
- Dung lucide icons khi can icon.
- Giu UI thuc dung, scan duoc, tranh refactor style lon neu khong lien quan.
- Khi them workflow moi, can xu ly loading/error/empty state.

Git/repo:

- Khong commit `.env`, runtime data, `.venv`, `node_modules`, cache.
- `.env.example` chi de placeholder/safe defaults.
- Giu commit scope ro theo feature/fix.
- Neu workspace dirty, khong revert thay doi khong do minh tao tru khi duoc yeu cau.

## Cac Quyet Dinh Ky Thuat Truoc Do

- Mac dinh retrieval la `hybrid`, khong chi vector-only.
- Hybrid = vector search + BM25 + Reciprocal Rank Fusion, sau do co the rerank.
- Query rewriting hien deterministic de tranh phu thuoc them vao LLM.
- Citation validation hien lightweight de nhanh, local va de test.
- Research mode dung deterministic step planning roi goi LLM active de synthesize.
- ChromaDB la primary vector backend, SQLite vector table la fallback development-friendly.
- Chroma failure phai hien trong health status, khong duoc che loi.
- Startup FastAPI tu dong chay `init_db()` va migrations.
- UI selected documents la filter chinh cho chat/retrieval/research; neu khong chon thi
  dung tat ca ready documents.
- Collections la nhom workspace lightweight, khong phai permission/security boundary.
- OpenAI-compatible endpoint la basic compatibility endpoint, khong phai full API clone.

## Constraint / Requirement Dac Biet

- Project uu tien privacy/local-first; API keys chi nam trong `.env` hoac secrets.
- `.env` bi ignore va khong duoc commit.
- Runtime folders bi ignore:
  - `data/raw`
  - `data/sqlite`
  - `data/chroma`
- Build/test tren Windows co the gap sandbox permission issue, dac biet Node `EPERM`
  voi path user; khi can, chay command ngoai sandbox voi approval.
- `rg.exe` tung bi `Access is denied` trong workspace nay; neu can search thi fallback
  sang PowerShell/Git commands.
- Node frontend dung Vite 4, yeu cau Node 16.20+.
- Sau khi doi embedding provider/model, can re-upload documents de vectors dung embedding moi.
- Neu them field API, can cap nhat ca backend Pydantic models va frontend TS types.

## TODO Tiep Theo

1. Mo rong integration tests khi workflow moi thay doi:
   - delete document cleanup vectors/chunks/files
   - OpenAI-compatible endpoint
   - API key middleware
   - ingestion failure paths cho PDF/DOCX parser errors
2. QA frontend bang browser local:
   - document selection
   - collection create/delete/add/remove/use ready docs
   - retrieval debug stages
   - research panel loading/error/result
   - citation validation badge
3. Cai thien citation validator:
   - detect citation format tot hon
   - map claim -> source chunks neu can
   - hien warning ro hon trong UI
4. Cai thien upload validation neu deploy public:
   - gioi han ZIP bomb/qua nhieu entries cho DOCX
   - reject file rong neu can
   - them integration tests cho upload gia mao
5. Cai thien reranking/query rewriting neu can chat luong:
   - optional provider-based rewrite
   - optional cross-encoder/local model reranker
   - benchmark retrieval precision voi test fixtures
6. Review schema migration runner:
   - them tests cho downgrade/duplicate migration behavior neu can
   - can nhac Alembic neu schema phuc tap hon
7. Review security/deployment:
   - API key middleware behavior
   - CORS defaults
   - upload size/file type hardening
8. Cap nhat docs khi them feature moi:
   - `README.md`
   - `docs/api.md`
   - `docs/architecture.md`
   - `docs/development.md`
