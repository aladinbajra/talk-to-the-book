#!/usr/bin/env python3
"""
Process book text into chunks based on the chunking plan from ingest output.

This script takes a book text and an ingest JSON file, then generates
chunks according to the specified chunking plan.
"""

import json
import argparse
import re
from pathlib import Path
from typing import List, Dict, Tuple
import hashlib
from dataclasses import dataclass, asdict


@dataclass
class Chunk:
    """Represents a single chunk of text."""
    chunk_id: str
    chunk_text: str
    start_loc: str
    end_loc: str
    chapter: int
    excerpt_hint: str
    word_count: int
    token_estimate: int


def estimate_tokens(text: str) -> int:
    """Rough token estimate (1 token ≈ 4 characters for English)."""
    return len(text) // 4


def generate_chunk_id(book_id: str, chapter: int, chunk_index: int) -> str:
    """Generate a deterministic chunk ID."""
    return f"{book_id}_ch{chapter:03d}_chunk{chunk_index:04d}"


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences (simple heuristic)."""
    # Split on sentence-ending punctuation followed by space
    sentences = re.split(r'([.!?]+)\s+', text)
    result = []
    for i in range(0, len(sentences) - 1, 2):
        if i + 1 < len(sentences):
            result.append(sentences[i] + sentences[i + 1])
        else:
            result.append(sentences[i])
    if len(sentences) % 2 == 1:
        result.append(sentences[-1])
    return [s.strip() for s in result if s.strip()]


def chunk_text(
    text: str,
    chunk_size_words: int,
    overlap_percent: float,
    prefer_chapter_boundaries: bool,
    chapter_markers: List[Tuple[int, str, int]] = None  # (chapter_num, title, start_char_pos)
) -> List[Chunk]:
    """
    Chunk text according to the specified plan.
    
    Args:
        text: Full book text
        chunk_size_words: Target chunk size in words
        overlap_percent: Percentage of overlap between chunks
        prefer_chapter_boundaries: Whether to prefer chapter boundaries
        chapter_markers: List of (chapter_num, title, start_char_pos) tuples
    
    Returns:
        List of Chunk objects
    """
    chunks = []
    words = text.split()
    total_words = len(words)
    
    overlap_words = int(chunk_size_words * overlap_percent / 100)
    step_size = chunk_size_words - overlap_words
    
    # Build chapter boundaries map if provided
    chapter_boundaries = {}
    if chapter_markers:
        for i, (ch_num, title, start_pos) in enumerate(chapter_markers):
            # Estimate word position from character position
            char_pos = start_pos
            word_pos = len(text[:char_pos].split())
            chapter_boundaries[word_pos] = (ch_num, title)
    
    chunk_index = 0
    current_pos = 0
    
    while current_pos < total_words:
        # Determine chunk end
        chunk_end = min(current_pos + chunk_size_words, total_words)
        
        # If prefer chapter boundaries, try to align
        if prefer_chapter_boundaries and chapter_boundaries:
            # Check if we're near a chapter boundary
            for boundary_pos, (ch_num, title) in sorted(chapter_boundaries.items()):
                if boundary_pos > current_pos and boundary_pos < chunk_end:
                    # Adjust chunk_end to chapter boundary
                    chunk_end = boundary_pos
                    break
        
        # Extract chunk text
        chunk_words = words[current_pos:chunk_end]
        chunk_text = ' '.join(chunk_words)
        
        # Determine chapter number
        chapter_num = 0
        if chapter_boundaries:
            for boundary_pos, (ch_num, title) in sorted(chapter_boundaries.items(), reverse=True):
                if boundary_pos <= current_pos:
                    chapter_num = ch_num
                    break
        
        # Generate chunk ID (using book_id from context - will be set later)
        chunk_id = f"chunk_{chunk_index:04d}"
        
        # Estimate location markers
        start_loc = f"word_{current_pos}"
        end_loc = f"word_{chunk_end}"
        
        # Create excerpt hint (first 50 chars)
        excerpt_hint = chunk_text[:50] + "..." if len(chunk_text) > 50 else chunk_text
        
        chunk = Chunk(
            chunk_id=chunk_id,
            chunk_text=chunk_text,
            start_loc=start_loc,
            end_loc=end_loc,
            chapter=chapter_num,
            excerpt_hint=excerpt_hint,
            word_count=len(chunk_words),
            token_estimate=estimate_tokens(chunk_text)
        )
        
        chunks.append(chunk)
        
        # Move to next chunk position
        if chunk_end >= total_words:
            break
        current_pos += step_size
        chunk_index += 1
    
    return chunks


def process_book_chunks(
    book_text: str,
    ingest_data: dict,
    book_id: str = None
) -> List[Dict]:
    """
    Process book into chunks using the ingest configuration.
    
    Args:
        book_text: Full book text
        ingest_data: Ingest JSON data
        book_id: Book ID (if None, uses book_id from ingest_data)
    
    Returns:
        List of chunk dictionaries ready for JSONL export
    """
    if book_id is None:
        book_id = ingest_data.get("book_id", "unknown")
    
    chunking_plan = ingest_data.get("chunking_plan", {})
    chapter_index = ingest_data.get("book_profile", {}).get("chapter_index", [])
    
    chunk_size_words = chunking_plan.get("recommended_chunk_size_words", 600)
    overlap_percent = chunking_plan.get("overlap_percent", 20)
    prefer_boundaries = chunking_plan.get("chunk_boundary_preference", "YES") == "YES"
    
    # Build chapter markers from chapter_index
    chapter_markers = []
    for ch_info in chapter_index:
        # Parse start_loc to estimate character position
        # This is a heuristic - actual implementation would need better parsing
        chapter_markers.append((
            ch_info.get("chapter_number", 0),
            ch_info.get("chapter_title", ""),
            0  # Would need actual character position mapping
        ))
    
    # Generate chunks
    chunks = chunk_text(
        book_text,
        chunk_size_words,
        overlap_percent,
        prefer_boundaries,
        chapter_markers if prefer_boundaries else None
    )
    
    # Update chunk IDs with book_id
    result = []
    for i, chunk in enumerate(chunks):
        chunk.chunk_id = generate_chunk_id(book_id, chunk.chapter, i)
        result.append(asdict(chunk))
    
    return result


def save_chunks_jsonl(chunks: List[Dict], output_path: str):
    """Save chunks to JSONL file."""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    print(f"✓ Saved {len(chunks)} chunks to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Process book text into chunks based on ingest configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "book_file",
        help="Path to the book text file"
    )
    
    parser.add_argument(
        "ingest_json",
        help="Path to the ingest JSON file"
    )
    
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output JSONL file path (default: chunks/{book_id}_chunks.jsonl)"
    )
    
    args = parser.parse_args()
    
    # Load book text
    print(f"Loading book from: {args.book_file}")
    book_text = Path(args.book_file).read_text(encoding='utf-8')
    print(f"✓ Loaded {len(book_text):,} characters")
    
    # Load ingest data
    print(f"Loading ingest config from: {args.ingest_json}")
    with open(args.ingest_json, 'r', encoding='utf-8') as f:
        ingest_data = json.load(f)
    print("✓ Loaded ingest configuration")
    
    # Process chunks
    print("\nProcessing chunks...")
    chunks = process_book_chunks(book_text, ingest_data)
    print(f"✓ Generated {len(chunks)} chunks")
    
    # Save output
    if args.output:
        output_path = args.output
    else:
        book_id = ingest_data.get("book_id", "unknown")
        output_dir = Path("chunks")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{book_id}_chunks.jsonl"
    
    save_chunks_jsonl(chunks, output_path)
    
    # Print statistics
    total_words = sum(c['word_count'] for c in chunks)
    avg_chunk_size = total_words / len(chunks) if chunks else 0
    
    print("\n" + "="*60)
    print("CHUNKING STATISTICS")
    print("="*60)
    print(f"Total chunks: {len(chunks)}")
    print(f"Total words: {total_words:,}")
    print(f"Average chunk size: {avg_chunk_size:.1f} words")
    print(f"Chunk size range: {min(c['word_count'] for c in chunks)} - {max(c['word_count'] for c in chunks)} words")
    print("="*60)


if __name__ == "__main__":
    main()
