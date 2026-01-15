#!/usr/bin/env bash
set -euo pipefail

# Simple load test (requires a ready BOOK_ID)
# Usage: BOOK_ID=... ./backend/scripts/load_test.sh

if [ -z "${BOOK_ID:-}" ]; then
  echo "Set BOOK_ID environment variable"
  exit 1
fi

N="${N:-50}"
CONC="${CONC:-10}"

echo "Running $N requests with concurrency $CONC against book $BOOK_ID"

seq 1 "$N" | xargs -I{} -P "$CONC" curl -sS -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d "{\"book_id\":\"$BOOK_ID\",\"question\":\"Summarize the main idea.\",\"history\":[]}" >/dev/null

echo "Done."

