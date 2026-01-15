import time
import requests


BASE = "http://localhost:8000"


def test_ingest_completes():
    with open("backend/acceptance/fixtures/sample_book.txt", "rb") as f:
        r = requests.post(
            f"{BASE}/api/v1/upload",
            files={"file": ("sample_book.txt", f, "text/plain")},
            data={"user_consent": "true"},
            timeout=30,
        )
    assert r.status_code == 200
    book_id = r.json()["book_id"]

    r2 = requests.post(f"{BASE}/api/v1/ingest/start", json={"book_id": book_id}, timeout=30)
    assert r2.status_code == 200

    deadline = time.time() + 240
    while time.time() < deadline:
        st = requests.get(f"{BASE}/api/v1/ingest/status", params={"book_id": book_id}, timeout=30).json()
        if st["status"] == "ready":
            return
        assert st["status"] != "error"
        time.sleep(2)

    raise AssertionError("ingest did not reach ready in time")

