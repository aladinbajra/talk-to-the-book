# Talk to the Book

A personal reading workspace with a searchable library, book processing and conversations linked to retrieved passages. The responsive interface supports PDF, TXT and ePub, processing retries, visible citations and confirmed deletion.

## Run the web app

Use Python 3.11+ and Node 20.9+. The frontend uses Next.js 16, React 19 and Tailwind CSS. The backend uses FastAPI, SQLAlchemy, Sentence Transformers and FAISS.

```sh
python -m venv .venv
# Activate .venv using the command for your shell.
python -m pip install -r backend/requirements.txt
cd backend
# Copy .env.example to .env and configure OPENAI_API_KEY.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000. The frontend forwards same-origin `/api/v1` requests to the backend. Set `BACKEND_URL` before building when the backend runs elsewhere. `NEXT_PUBLIC_API_URL` is an optional direct browser origin; it normally stays empty.

1. Add a book and confirm you have the right to upload it.
2. Follow its status in the library; active processing refreshes automatically.
3. Open a ready book, ask a question and expand the passages behind the answer.
4. Retry a failed processing job without uploading the book again, or confirm deletion to remove its files, vector index and database records.

The first real embedding request downloads the configured Sentence Transformers model. Startup, health checks and the regression suite do not download a model. OpenAI processing uses the configured `DEFAULT_LLM_MODEL` (default `gpt-4o-mini`), bounded timeouts and asynchronous calls.

## Processing and retrieval

- Upload consent is multipart form data, matching the browser. Reads stop at the configured byte limit; empty and obviously invalid files are rejected.
- Temporary extraction files work on Windows and Unix and are cleaned on errors. Paragraphs and chapter positions survive normalization. Short chapters no longer cause words to be skipped.
- Ingestion retries replace their own deterministic chunks. A failed run leaves a visible error state rather than an unusable job.
- Embedding models load lazily and are reused per process. New normalized indices use inner-product cosine search. Existing squared-L2 indices use `1 - distance / 2`, preserving cosine thresholds without requiring re-ingestion.
- Citation IDs must belong to retrieved passages from the selected book. Unsupported citations produce `UNKNOWN IN BOOK`; excerpts are loaded from stored passages, not invented by the model. This checks citation provenance; it does not prove every generated sentence is factually entailed by the passage.
- When encryption is configured, uploaded bytes are encrypted before storage so no plaintext original is left beside the encrypted upload. Back up the key separately.

## Configuration and data

See `backend/.env.example` and `frontend/.env.example`. Local SQLite, uploaded books, indices, logs, API keys and build/test artifacts are ignored by Git. Storage and database paths must point to persistent volumes in a deployed instance. Docker Compose stores the SQLite database inside the storage volume and uses a Node 22 frontend image.

This application is for a trusted personal instance. The API currently has no multi-user authentication or ownership boundary. Add access control before exposing it to other users. Background ingestion runs in the application process; a durable job queue is a separate deployment improvement.

## Tests without API credits or model downloads

```sh
python -m pip install -r backend/requirements-test.txt
cd backend
python -m pytest tests -q
python -m black --check app
python -m isort --check-only app
```

```sh
cd frontend
npm ci
npm run lint
npm run build
npx playwright install chromium
npm run test:e2e
```

Backend tests use a fresh in-memory database, temporary storage, deterministic test embeddings, real FAISS indices and simulated LLM responses. Browser tests start the production frontend on port 3720 and mock API responses on desktop and mobile. A real provider transaction and a real model download are separate checks.

See [the verification record](docs/verification-2026-11-19.md).

## Original command-line tools

The root-level ingest prompt, schema, chunking, embedding and runtime scripts remain available as a separate CLI workflow. Their setup and configuration are described in [QUICKSTART.md](QUICKSTART.md), [PROJECT_README.md](PROJECT_README.md) and [API_EXAMPLES.md](API_EXAMPLES.md). Install the root `requirements.txt` for those tools; it is separate from the web backend.
