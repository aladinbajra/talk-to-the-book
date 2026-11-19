import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import faiss
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.models import Book, Chunk
from app.main import app
from app.services.chunker import Chunker
from app.services.embedding_service import EmbeddingService
from app.services.ingest import IngestService
from app.services.query import QueryService
from app.services.text_processor import TextProcessor

client = TestClient(app)
TEXT = b"Chapter 1\nA seed needs water and sunlight to grow. Plants turn sunlight into energy.\n\nChapter 2\nHealthy soil helps the roots develop and retain water."


def upload(content=TEXT, consent="true", filename="garden.txt"):
    return client.post(
        "/api/v1/upload",
        files={"file": (filename, content, "text/plain")},
        data={"user_consent": consent},
    )


class OfflineEncoder:
    def encode(self, texts, **kwargs):
        return np.tile(np.array([[1.0, 0.0, 0.0]], dtype="float32"), (len(texts), 1))


@pytest.fixture
def offline_ai(monkeypatch):
    monkeypatch.setattr(EmbeddingService, "_load_model", lambda self: OfflineEncoder())
    monkeypatch.setattr(
        IngestService,
        "_generate_book_profile",
        AsyncMock(
            return_value={
                "book_metadata": {"title": "A small garden", "author": "Test Author"},
                "book_profile": {},
            }
        ),
    )

    async def generate(self, **kwargs):
        return self.validate_answer(
            {
                "answer": "Plants need water and sunlight.",
                "confidence": 0.9,
                "sources": [kwargs["chunks"][0]["chunk_id"]],
            },
            kwargs["chunks"],
        )

    monkeypatch.setattr(QueryService, "_generate_answer", generate)


def test_multipart_consent_matches_the_browser_contract():
    assert upload(consent="false").status_code == 400
    response = upload()
    assert response.status_code == 200
    assert response.json()["status"] == "uploaded"


@pytest.mark.parametrize(
    "content,filename,status",
    [
        (b"", "empty.txt", 400),
        (b"not a pdf", "fake.pdf", 400),
        (b"not an archive", "fake.epub", 400),
        (b"executable", "app.exe", 400),
    ],
)
def test_invalid_uploads_are_not_saved(content, filename, status):
    assert upload(content=content, filename=filename).status_code == status
    assert client.get("/api/v1/books").json()["books"] == []


def test_upload_read_limit(monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 16)
    assert upload(content=b"x" * 17).status_code == 413
    assert client.get("/api/v1/books").json()["books"] == []


def test_encrypted_upload_leaves_no_plaintext(monkeypatch, isolated_database):
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", "test-key-for-encryption-only")
    book_id = upload().json()["book_id"]
    with isolated_database() as db:
        book = db.get(Book, book_id)
        path = Path(book.file_path)
        assert path.name.endswith(".encrypted")
        assert list(path.parent.iterdir()) == [path]
        assert TEXT not in path.read_bytes()
        from app.services.encryption import EncryptionService

        assert EncryptionService().decrypt_bytes(path.read_bytes()) == TEXT


def test_upload_process_query_and_delete(offline_ai):
    book_id = upload().json()["book_id"]
    response = client.post("/api/v1/ingest/start", json={"book_id": book_id})
    assert response.status_code == 200
    assert (
        client.get("/api/v1/ingest/status", params={"book_id": book_id}).json()[
            "status"
        ]
        == "ready"
    )
    books = client.get("/api/v1/books").json()["books"]
    assert books[0]["title"] == "A small garden"
    assert books[0]["author"] == "Test Author"
    answer = client.post(
        "/api/v1/query",
        json={"book_id": book_id, "question": "What helps a seed grow?"},
    )
    assert answer.status_code == 200
    assert answer.json()["sources"]
    assert "water" in answer.json()["source_details"][0]["excerpt"]
    assert client.get("/api/v1/books").json()["books"][0]["question_count"] == 1
    assert (
        client.post("/api/v1/delete_book", json={"book_id": book_id}).status_code == 200
    )
    assert not (Path(settings.STORAGE_PATH) / "books" / book_id).exists()
    assert not list(Path(settings.FAISS_INDEX_PATH).glob(f"{book_id}*"))
    assert client.get("/api/v1/books").json()["books"] == []


def test_failed_ingest_can_be_retried_without_duplicate_chunks(
    offline_ai, monkeypatch, isolated_database
):
    book_id = upload().json()["book_id"]
    monkeypatch.setattr(
        IngestService,
        "_generate_book_profile",
        AsyncMock(side_effect=RuntimeError("temporary provider failure")),
    )
    client.post("/api/v1/ingest/start", json={"book_id": book_id})
    assert (
        client.get("/api/v1/ingest/status", params={"book_id": book_id}).json()[
            "status"
        ]
        == "error"
    )
    monkeypatch.setattr(
        IngestService,
        "_generate_book_profile",
        AsyncMock(return_value={"book_profile": {}}),
    )
    client.post("/api/v1/ingest/start", json={"book_id": book_id})
    assert (
        client.get("/api/v1/ingest/status", params={"book_id": book_id}).json()[
            "status"
        ]
        == "ready"
    )
    with isolated_database() as db:
        chunks = db.query(Chunk).filter_by(book_id=book_id).all()
        assert len(chunks) == len({chunk.chunk_id for chunk in chunks})


def test_lightweight_api_startup_does_not_load_a_transformer():
    service = EmbeddingService()
    assert service.model is None
    assert "sentence_transformers" not in sys.modules
    assert client.get("/health").status_code == 200


@pytest.mark.parametrize("options", [{"chunk_size": 0}, {"overlap_percent": 100}])
def test_invalid_ingest_options_are_rejected(options):
    assert (
        client.post(
            "/api/v1/ingest/start", json={"book_id": "missing", "options": options}
        ).status_code
        == 422
    )


@pytest.mark.parametrize("question", ["", "   ", "x" * 4001])
def test_question_validation(question):
    assert (
        client.post(
            "/api/v1/query", json={"book_id": "missing", "question": question}
        ).status_code
        == 422
    )


@pytest.mark.parametrize("sources", [[], ["invented"], ["a", "invented"], None])
def test_unsupported_citations_cannot_be_reported_as_evidence(sources):
    result = QueryService.validate_answer(
        {"answer": "A claim", "sources": sources, "confidence": 0.99},
        [{"chunk_id": "a", "chunk_text": "A real passage"}],
    )
    assert result["answer"] == "UNKNOWN IN BOOK"
    assert result["sources"] == []
    assert result["confidence"] == 0


def test_citation_details_come_from_the_retrieved_passages():
    result = QueryService.validate_answer(
        {
            "answer": "A supported answer",
            "sources": ["a", "a"],
            "confidence": float("nan"),
            "source_details": [{"excerpt": "invented"}],
        },
        [{"chunk_id": "a", "chunk_text": "Real evidence", "chapter": 2}],
    )
    assert result["sources"] == ["a"]
    assert result["source_details"][0]["excerpt"] == "Real evidence"
    assert result["confidence"] == 0


def test_short_chapters_do_not_drop_words_or_cross_boundaries():
    first = " ".join(f"a{i}" for i in range(7))
    second = " ".join(f"b{i}" for i in range(80))
    text = first + "\n" + second
    chunks = Chunker(30, 20).chunk_text(
        text, "book", [(1, "First", 0), (2, "Second", len(first) + 1)]
    )
    assert chunks[0].chunk_text == first
    assert set(" ".join(chunk.chunk_text for chunk in chunks).split()) == set(
        text.split()
    )
    assert all(
        not ("a0" in chunk.chunk_text and "b0" in chunk.chunk_text) for chunk in chunks
    )


def test_text_normalization_preserves_chapter_positions():
    text = TextProcessor.normalize_text(
        "Chapter 1\r\nOne short line.\r\n\r\nChapter 2\r\nAnother line."
    )
    assert "\nChapter 2\n" in text
    chapters = TextProcessor.detect_chapters(text)
    assert [chapter[0] for chapter in chapters] == [1, 2]
    assert text[chapters[1][2] :].lstrip().startswith("Chapter 2")


def test_normalization_keeps_numbers_that_may_be_source_content():
    assert (
        TextProcessor.normalize_text("The year was\n2026\nand the answer was\n42")
        == "The year was\n2026\nand the answer was\n42"
    )


@pytest.mark.parametrize("metric", ["legacy_l2", "cosine"])
def test_cosine_threshold_works_for_existing_and_new_indices(
    metric, offline_ai, isolated_database, monkeypatch
):
    book_id = "indexed-book"
    with isolated_database() as db:
        db.add(
            Book(
                book_id=book_id,
                file_path="unused.txt",
                file_format="txt",
                ingest_status="ready",
                book_profile={"book_profile": {"title": "Evidence"}},
            )
        )
        db.add(
            Chunk(
                chunk_id="passage",
                book_id=book_id,
                chunk_text="Plants need water and sunlight.",
            )
        )
        db.commit()
    folder = Path(settings.FAISS_INDEX_PATH)
    folder.mkdir(parents=True)
    index = faiss.IndexFlatL2(3) if metric == "legacy_l2" else faiss.IndexFlatIP(3)
    index.add(np.array([[0.7, np.sqrt(0.51), 0]], dtype="float32"))
    faiss.write_index(index, str(folder / f"{book_id}.faiss"))
    (folder / f"{book_id}_metadata.json").write_text(
        json.dumps({"chunk_ids": ["passage"]})
    )
    monkeypatch.setattr(settings, "SIMILARITY_THRESHOLD", 0.6)
    response = client.post(
        "/api/v1/query", json={"book_id": book_id, "question": "What helps plants?"}
    )
    assert response.status_code == 200
    assert response.json()["sources"] == ["passage"]
