# API Examples

## Upload Book

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@my_book.pdf" \
  -F "user_consent=true"
```

Response:
```json
{
  "book_id": "abc-123-def",
  "status": "uploaded",
  "filename": "my_book.pdf",
  "file_size": 1234567,
  "message": "File uploaded successfully. Start ingest with /ingest/start"
}
```

## Start Ingest

```bash
curl -X POST http://localhost:8000/api/v1/ingest/start \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "abc-123-def",
    "options": {
      "chunk_size": 600,
      "overlap_percent": 20
    }
  }'
```

Response:
```json
{
  "ingest_job_id": "abc-123-def",
  "book_id": "abc-123-def",
  "status": "started",
  "message": "Ingest process started"
}
```

## Check Ingest Status

```bash
curl http://localhost:8000/api/v1/ingest/status?book_id=abc-123-def
```

Response:
```json
{
  "book_id": "abc-123-def",
  "status": "ready",
  "progress": 1.0,
  "issues": []
}
```

## Query Book

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "abc-123-def",
    "question": "What is the main theme of this book?",
    "history": [],
    "options": {
      "style": "detailed"
    }
  }'
```

Response:
```json
{
  "answer": "The main theme is...",
  "confidence": 0.85,
  "style_score": "interpretive",
  "sources": ["chunk_001", "chunk_002"],
  "explanation": "Based on chapters 1 and 3",
  "notes": null
}
```

## List Books

```bash
curl http://localhost:8000/api/v1/books
```

Response:
```json
{
  "books": [
    {
      "book_id": "abc-123-def",
      "title": "My Book",
      "author": "Author Name",
      "ingest_status": "ready",
      "question_count": 5,
      "last_used": "2024-01-01T12:00:00Z"
    }
  ]
}
```

## Submit Feedback

```bash
curl -X POST http://localhost:8000/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "query_id": "query-123",
    "feedback": "up",
    "comment": "Great answer!"
  }'
```

## Delete Book

```bash
curl -X POST http://localhost:8000/api/v1/delete_book \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": "abc-123-def"
  }'
```

## Get Metrics

```bash
curl http://localhost:8000/metrics
```

Returns Prometheus format metrics.
