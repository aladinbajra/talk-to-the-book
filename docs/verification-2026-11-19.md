# Verification — 19 November 2026

The web app now provides a responsive personal library, searchable author/title cards, processing filters, active-job polling, upload validation, recoverable processing, source excerpts in conversations, query retries and confirmed deletion.

Upload consent is parsed as multipart data. Upload reads are bounded, temporary extraction is portable, numeric source lines and chapter positions are preserved, and short chapters no longer skip words. Retry replaces the book's previous deterministic chunks. An atomic status update prevents duplicate job starts. Failures roll back their transaction and leave a visible retryable status.

Embedding and reranking models load lazily and are reused. Blocking inference runs off the async request loop. New normalized indices use cosine inner-product search; existing squared-L2 indices are interpreted correctly. Returned citations must be drawn from the retrieved passages of the selected book. Source excerpts come from stored text. Unsupported citations return `UNKNOWN IN BOOK`, and invalid confidence values cannot escape in the response.

Encrypted uploads are encrypted before storage without a parallel plaintext original. Deletion removes book files, index artifacts and related database records; active jobs cannot be deleted. Storage deletion checks resolved paths before recursive removal.

The frontend was upgraded from Next.js 14 / React 18 to a consistent published Next.js 16.2.6 / React 19 release, with a lockfile, local lint configuration and a Node 22 Docker image. The browser uses a same-origin API proxy. Docker Compose persists SQLite in the storage volume.

## Passed checks

- 32 backend tests, including multipart consent, bounded/invalid uploads, encryption, full upload–ingest–query–delete flow, retry after provider failure, chunk coverage, citation provenance, missing-book/input errors and compatibility with real FAISS L2/IP indices.
- Black and isort checks used by the repository's existing CI.
- Frontend ESLint and production build.
- 10 Playwright checks across desktop and mobile: library search/reset, upload consent and processing, source expansion, delete confirmation and query failure/retry without duplicating the question.

Backend tests use fresh in-memory SQLite, temporary storage, real FAISS indices, deterministic test embeddings and simulated LLM calls. They require no API credits or model downloads. Browser tests mock the API contract separately.

## Limits

Real model download, real provider responses and container deployment were not exercised. Citation validation establishes provenance, not semantic proof of every generated claim. The API remains a trusted single-user application; public multi-user use requires authentication and ownership checks. Background jobs are in-process and need a durable queue for restart recovery. The root CLI tools remain a separate workflow.

Async client lifecycle, timeouts and retries follow the [official OpenAI Python SDK documentation](https://developers.openai.com/api/reference/python).
