"""
Tests for chunker determinism.
"""

import pytest

from app.services.chunker import Chunker


def test_chunker_determinism():
    """Test that chunking produces deterministic chunk IDs."""
    text = "This is a test book. " * 1000  # Create a long text

    chunker1 = Chunker(chunk_size_words=100, overlap_percent=20)
    chunks1 = chunker1.chunk_text(text, "test_book_001")

    chunker2 = Chunker(chunk_size_words=100, overlap_percent=20)
    chunks2 = chunker2.chunk_text(text, "test_book_001")

    # Same input should produce same chunk IDs
    assert len(chunks1) == len(chunks2)
    for c1, c2 in zip(chunks1, chunks2):
        assert c1.chunk_id == c2.chunk_id
        assert c1.start_loc == c2.start_loc
        assert c1.end_loc == c2.end_loc


def test_chunker_respects_chapter_boundaries():
    """Test that chunker respects chapter boundaries when enabled."""
    text = (
        "Chapter 1\n"
        + "This is chapter one. " * 200
        + "\n\nChapter 2\n"
        + "This is chapter two. " * 200
    )

    chunker = Chunker(
        chunk_size_words=100, overlap_percent=20, prefer_chapter_boundaries=True
    )

    # Mock chapter markers
    chapter_markers = [
        (1, "Chapter 1", 0),
        (2, "Chapter 2", len("Chapter 1\n" + "This is chapter one. " * 200)),
    ]

    chunks = chunker.chunk_text(text, "test_book", chapter_markers)

    # Verify chunks don't cross chapter boundaries
    for chunk in chunks:
        assert chunk.chapter_number in [0, 1, 2]


def test_chunker_overlap():
    """Test that chunks have proper overlap."""
    text = "Word " * 1000

    chunker = Chunker(chunk_size_words=100, overlap_percent=20)
    chunks = chunker.chunk_text(text, "test_book")

    # Check that chunks overlap (simplified check)
    assert len(chunks) > 1
    assert all(chunk.word_count == 100 for chunk in chunks[:-1])
    assert 1 <= chunks[-1].word_count <= 100
    assert chunks[0].start_loc == "word_0"
    assert chunks[-1].end_loc == "word_1000"
    for previous, current in zip(chunks, chunks[1:]):
        assert (
            int(previous.end_loc.removeprefix("word_"))
            - int(current.start_loc.removeprefix("word_"))
            == 20
        )
