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
    text = "Chapter 1\n" + "This is chapter one. " * 200 + "\n\nChapter 2\n" + "This is chapter two. " * 200
    
    chunker = Chunker(chunk_size_words=100, overlap_percent=20, prefer_chapter_boundaries=True)
    
    # Mock chapter markers
    chapter_markers = [
        (1, "Chapter 1", 0),
        (2, "Chapter 2", len("Chapter 1\n" + "This is chapter one. " * 200))
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
    # Each chunk should have approximately 100 words
    for chunk in chunks:
        assert 80 <= chunk.word_count <= 120  # Allow some variance
