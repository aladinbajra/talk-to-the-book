# RUNBOOK — Talk to the Book (Backend)

This runbook covers common backend incidents and operational procedures.

## Key SLOs
- **p95 query latency**: <= 3s (50 concurrent users)
- **unknown_rate**: <= 0.35 on negative prompts
- **success_rate**: >= 0.98

## Quick Triage Checklist
- Check `/health` for service availability.
- Check `/metrics` for spikes in latency, errors, unknown rate, cache misses.
- Check logs (`logs/app.log`) for stack traces or repeated failures.
- Confirm Redis is reachable (if enabled).
- Confirm FAISS index files exist for the book under `storage/indices/`.

## Incident: Queries returning UNKNOWN too often
1. Verify ingest completed (`/api/v1/ingest/status` is `ready`).
2. Inspect retrieval candidates (`retrieval_candidates` metric).
3. Check similarity threshold (`SIMILARITY_THRESHOLD`). If too high, retrieval returns none.
4. Confirm embeddings/index exist:
   - `storage/indices/{book_id}.faiss`
   - `storage/indices/{book_id}_metadata.json`
   - `storage/embeddings/{book_id}_embeddings.npz`
5. If validator is rejecting answers, look for `notes=validator_rejected`.

## Incident: High latency (p95 > 3s)
1. Check `query_latency_seconds` p95 and identify which stage:
   - `retrieval_latency_seconds`
   - `rerank_latency_seconds`
   - `generation_latency_seconds`
2. If reranking is enabled and slow, disable temporarily:
   - set `RERANK_ENABLED=false`
3. If cache hit rate is low, increase TTL:
   - `CACHE_TTL_SECONDS=600`
4. If LLM API is slow, consider a faster model or increase caching.

## Incident: Redis down
Backend falls back to in-memory LRU automatically.
1. Restore Redis service.
2. Confirm `cache_hit_total` starts increasing again.

## Procedure: Rebuild index for a book
1. Delete the book (optional) with `/api/v1/delete_book` and re-upload.
2. Or manually:
   - remove `storage/indices/{book_id}*`
   - remove `storage/embeddings/{book_id}*`
   - rerun ingest `/api/v1/ingest/start`

## Procedure: Rotate API keys
1. Update secret store / environment variables (`OPENAI_API_KEY`).
2. Restart backend deployment.
3. Verify via a single `/api/v1/query`.

## Procedure: DB restore (SQLite MVP)
1. Stop backend
2. Replace `talk_to_the_book.db` from backup
3. Restart backend

