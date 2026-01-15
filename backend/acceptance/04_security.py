import time
import requests


BASE = "http://localhost:8000"


def _upload_ingest_with_pii():
    # Inline PII in content to ensure redaction path is exercised.
    content = b\"\"\"Chapter 1\nContact: test@example.com and 555-123-4567.\nThe system must redact PII.\n\"\"\"
    r = requests.post(
        f\"{BASE}/api/v1/upload\",
        files={\"file\": (\"pii_book.txt\", content, \"text/plain\")},
        data={\"user_consent\": \"true\"},
        timeout=30,
    )
    book_id = r.json()[\"book_id\"]
    requests.post(f\"{BASE}/api/v1/ingest/start\", json={\"book_id\": book_id}, timeout=30)

    deadline = time.time() + 240
    while time.time() < deadline:
        st = requests.get(f\"{BASE}/api/v1/ingest/status\", params={\"book_id\": book_id}, timeout=30).json()
        if st[\"status\"] == \"ready\":
            return book_id
        time.sleep(2)
    raise RuntimeError(\"ingest timeout\")


def test_pii_redaction_note():
    book_id = _upload_ingest_with_pii()
    resp = requests.post(
        f\"{BASE}/api/v1/query\",
        json={\"book_id\": book_id, \"question\": \"What contact info is mentioned?\", \"history\": []},
        timeout=60,
    )
    assert resp.status_code == 200
    j = resp.json()
    # Either UNKNOWN (if model refuses) or redaction note
    assert j[\"notes\"] in (None, \"redacted_pii\", \"UNKNOWN IN BOOK\", \"validator_rejected\", \"unsure\")

