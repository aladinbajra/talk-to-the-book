"""
Deterministic chunking service.
"""
import hashlib
import re
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class Chunk:
    """Chunk data structure."""
    chunk_id: str
    chunk_text: str
    start_loc: str
    end_loc: str
    chapter_number: int
    excerpt_hint: str
    token_estimate: int
    word_count: int


class Chunker:
    """Deterministic chunking service."""
    
    def __init__(
        self,
        chunk_size_words: int = 600,
        overlap_percent: int = 20,
        prefer_chapter_boundaries: bool = True
    ):
        self.chunk_size_words = chunk_size_words
        self.overlap_percent = overlap_percent
        self.prefer_chapter_boundaries = prefer_chapter_boundaries
        self.overlap_words = int(chunk_size_words * overlap_percent / 100)
        self.step_size = chunk_size_words - self.overlap_words
    
    def generate_chunk_id(
        self,
        book_id: str,
        start_loc: str,
        end_loc: str
    ) -> str:
        """Generate deterministic chunk ID."""
        data = f"{book_id}:{start_loc}:{end_loc}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
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
        self,
        text: str,
        book_id: str,
        chapter_markers: List[Tuple[int, str, int]] = None
    ) -> List[Chunk]:
        """
        Chunk text deterministically.
        
        Args:
            text: Full text to chunk
            book_id: Book identifier
            chapter_markers: List of (chapter_num, title, start_char_pos)
        
        Returns:
            List of Chunk objects
        """
        words = text.split()
        total_words = len(words)
        chunks = []
        
        # Build chapter boundaries map
        chapter_boundaries = {}
        if chapter_markers:
            for ch_num, title, start_pos in chapter_markers:
                # Estimate word position from character position
                char_pos = start_pos
                word_pos = len(text[:char_pos].split())
                chapter_boundaries[word_pos] = (ch_num, title)
        
        chunk_index = 0
        current_pos = 0
        
        while current_pos < total_words:
            # Determine chunk end
            chunk_end = min(current_pos + self.chunk_size_words, total_words)
            
            # If prefer chapter boundaries, try to align
            if self.prefer_chapter_boundaries and chapter_boundaries:
                for boundary_pos, (ch_num, title) in sorted(chapter_boundaries.items()):
                    if boundary_pos > current_pos and boundary_pos < chunk_end:
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
            
            # Generate locations
            start_loc = f"word_{current_pos}"
            end_loc = f"word_{chunk_end}"
            
            # Generate chunk ID
            chunk_id = self.generate_chunk_id(book_id, start_loc, end_loc)
            
            # Create excerpt hint
            excerpt_hint = chunk_text[:50] + "..." if len(chunk_text) > 50 else chunk_text
            
            # Estimate tokens (rough: 1 token ≈ 4 chars)
            token_estimate = len(chunk_text) // 4
            
            chunk = Chunk(
                chunk_id=chunk_id,
                chunk_text=chunk_text,
                start_loc=start_loc,
                end_loc=end_loc,
                chapter_number=chapter_num,
                excerpt_hint=excerpt_hint,
                token_estimate=token_estimate,
                word_count=len(chunk_words)
            )
            
            chunks.append(chunk)
            
            # Move to next chunk
            if chunk_end >= total_words:
                break
            current_pos += self.step_size
            chunk_index += 1
        
        return chunks
