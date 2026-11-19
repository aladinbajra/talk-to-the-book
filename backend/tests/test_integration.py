"""
Integration tests for end-to-end flow.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_books_list_endpoint():
    """Test books listing endpoint."""
    response = client.get("/api/v1/books")
    assert response.status_code == 200
    assert "books" in response.json()


def test_upload_endpoint_invalid_file():
    """Test upload endpoint with invalid file."""
    response = client.post(
        "/api/v1/upload",
        files={"file": ("test.exe", b"fake content", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_query_endpoint_no_book():
    """Test query endpoint with non-existent book."""
    response = client.post(
        "/api/v1/query",
        json={"book_id": "non-existent", "question": "What is this book about?"},
    )
    assert response.status_code == 404
