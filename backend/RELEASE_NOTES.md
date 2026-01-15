## Release backend-next

### Day 1
- Created `release/backend-next` branch.
- Added runtime system prompt (`app/core/system_prompt_runtime.txt`) for strict JSON-only + source-only behavior.
- Added runtime validator (`app/core/response_validator.py`) with schema checks, quote-length rule, and entity-in-chunks provenance heuristic.
- Added cache layer (`app/services/cache.py`) with Redis + in-memory LRU fallback.
- Hardened query orchestration (`app/services/query.py`) with caching, PII redaction, validator gate, and conservative confidence.

