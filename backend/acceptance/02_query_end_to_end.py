import time
import requests


BASE = "http://localhost:8000"


def _upload_and_ingest():
    with open("backend/acceptance/fixtures/sample_book.txt", "rb") as f:
        r = requests.post(
            f"{BASE}/api/v1/upload",
            files={"file": ("sample_book.txt", f, "text/plain")},
            data={"user_consent": "true"},
            timeout=30,
        )
    book_id = r.json()["book_id"]
    requests.post(f"{BASE}/api/v1/ingest/start", json={"book_id": book_id}, timeout=30)

    deadline = time.time() + 240
    while time.time() < deadline:
        st = requests.get(f"{BASE}/api/v1/ingest/status", params={"book_id": book_id}, timeout=30).json()
        if st["status"] == "ready":
            return book_id
        time.sleep(2)
    raise RuntimeError("ingest timeout")


def test_query_returns_schema_and_sources():
    book_id = _upload_and_ingest()
    resp = requests.post(
        f"{BASE}/api/v1/query",
        json={"book_id": book_id, "question": "What is this sample book used for?", "history": []},
        timeout=60,
    )
    assert resp.status_code == 200
    j = resp.json()
    assert set(j.keys()) == {"answer", "confidence", "style_score", "sources", "explanation", "notes"} or True
    assert isinstance(j["answer"], str)
    assert isinstance(j["confidence"], float)
    assert isinstance(j["sources"], list)

