"""
Text processing utilities for extracting text from various formats.
"""
import pdfplumber
import ebooklib
from ebooklib import epub
from pathlib import Path
import re
from typing import List, Tuple, Optional


class TextProcessor:
    """Process text from various file formats."""
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extract text from PDF file."""
        text_parts = []
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        
        return "\n".join(text_parts)
    
    @staticmethod
    def extract_text_from_epub(file_path: str) -> str:
        """Extract text from ePub file."""
        book = epub.read_epub(file_path)
        text_parts = []
        
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                # Extract text from HTML
                content = item.get_content().decode('utf-8')
                # Simple HTML tag removal
                text = re.sub(r'<[^>]+>', '', content)
                text = re.sub(r'\s+', ' ', text).strip()
                if text:
                    text_parts.append(text)
        
        return "\n".join(text_parts)
    
    @staticmethod
    def extract_text_from_txt(file_path: str) -> str:
        """Extract text from plain text file."""
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                return Path(file_path).read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        
        raise ValueError(f"Could not decode file {file_path}")
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text: whitespace, headers/footers removal."""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove common headers/footers (simple heuristic)
        lines = text.split('\n')
        filtered_lines = []
        for line in lines:
            # Skip lines that look like page numbers
            if re.match(r'^\s*\d+\s*$', line):
                continue
            # Skip very short lines that might be headers
            if len(line.strip()) < 3:
                continue
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    @staticmethod
    def detect_chapters(text: str) -> List[Tuple[int, str, int]]:
        """
        Detect chapters in text.
        Returns list of (chapter_number, chapter_title, start_char_position).
        """
        chapters = []
        
        # Pattern 1: "Chapter 1", "Chapter 2", etc.
        pattern1 = re.compile(r'(?i)^\s*(?:chapter|ch\.?)\s*(\d+)[:.\s]*(.*?)$', re.MULTILINE)
        
        # Pattern 2: Numbered headings
        pattern2 = re.compile(r'^\s*(\d+)[:.\s]+(.+?)$', re.MULTILINE)
        
        # Find all matches
        matches = []
        for match in pattern1.finditer(text):
            matches.append((match.start(), int(match.group(1)), match.group(2).strip()))
        
        for match in pattern2.finditer(text):
            chapter_num = int(match.group(1))
            title = match.group(2).strip()
            # Only add if not already found by pattern1
            if not any(m[1] == chapter_num for m in matches):
                matches.append((match.start(), chapter_num, title))
        
        # Sort by position
        matches.sort(key=lambda x: x[0])
        
        return matches
    
    @staticmethod
    def extract_text(file_path: str, file_format: str) -> str:
        """Extract text from file based on format."""
        if file_format == "pdf":
            return TextProcessor.extract_text_from_pdf(file_path)
        elif file_format == "epub":
            return TextProcessor.extract_text_from_epub(file_path)
        elif file_format == "txt":
            return TextProcessor.extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
