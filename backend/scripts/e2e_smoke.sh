#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/docker-compose.backend.staging.yml"
FIXTURE="$ROOT_DIR/backend/acceptance/fixtures/sample_book.txt"

echo "Using compose: $COMPOSE_FILE"

if [ ! -f "$FIXTURE" ]; then
  echo "Missing fixture: $FIXTURE"
  exit 1
fi

echo "Starting backend stack..."
docker compose -f "$COMPOSE_FILE" up -d --build backend redis prometheus

echo "Waiting for backend to be healthy..."
for i in {1..60}; do
  if curl -fsS "http://localhost:8000/health" >/dev/null; then
    echo "Backend is healthy."
    break
  fi
  sleep 2
done

echo "Uploading fixture book..."
UPLOAD_RESP=$(curl -fsS -X POST "http://localhost:8000/api/v1/upload" \
  -F "file=@${FIXTURE}" \
  -F "user_consent=true")

BOOK_ID=$(python -c "import json,sys; print(json.loads(sys.argv[1])['book_id'])" "$UPLOAD_RESP")
echo "BOOK_ID=$BOOK_ID"

echo "Starting ingest..."
curl -fsS -X POST "http://localhost:8000/api/v1/ingest/start" \
  -H "Content-Type: application/json" \
  -d "{\"book_id\":\"$BOOK_ID\"}" >/dev/null

echo "Waiting for ingest ready..."
for i in {1..180}; do
  STATUS=$(curl -fsS "http://localhost:8000/api/v1/ingest/status?book_id=$BOOK_ID" | python -c "import json,sys; print(json.load(sys.stdin)['status'])")
  if [ "$STATUS" = "ready" ]; then
    echo "Ingest ready."
    break
  fi
  if [ "$STATUS" = "error" ]; then
    echo "Ingest failed."
    exit 1
  fi
  sleep 2
done

echo "Querying..."
QUERY_RESP=$(curl -fsS -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d "{\"book_id\":\"$BOOK_ID\",\"question\":\"What is this sample book about?\",\"history\":[]}")

echo "$QUERY_RESP" | python -c "import json,sys; j=json.load(sys.stdin); assert 'answer' in j and 'sources' in j; print('OK query schema')"

echo "Submitting feedback..."
echo "Smoke test completed."

echo "Stopping stack..."
docker compose -f "$COMPOSE_FILE" down

