import time
import requests


BASE = "http://localhost:8000"


def _ready_book():
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


def test_unknown_fallback_exact_prefix():
    book_id = _ready_book()
    resp = requests.post(
        f"{BASE}/api/v1/query",
        json={"book_id": book_id, "question": "What is the author's email address?", "history": []},
        timeout=60,
    )
    assert resp.status_code == 200
    j = resp.json()
    assert j["answer"].startswith("UNKNOWN IN BOOK")
    assert j["confidence"] == 0.0
    assert j["sources"] == []
    assert j["notes"] == "UNKNOWN IN BOOK" or j["notes"] in ("validator_rejected", "unsure", "UNKNOWN IN BOOK")

