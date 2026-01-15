"""
Ingest service for processing books.
"""
import json
import os
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any
import numpy as np

from app.db.database import SessionLocal
from app.db.models import Book, Chunk
from app.services.text_processor import TextProcessor
from app.services.chunker import Chunker
from app.services.storage import StorageService
from app.services.embedding_service import EmbeddingService
from app.core.config import settings
from app.core.metrics import ingest_duration_seconds
import time


class IngestService:
    """Service for ingesting books."""
    
    def __init__(self):
        self.text_processor = TextProcessor()
        self.storage_service = StorageService()
        self.embedding_service = EmbeddingService()
    
    async def process_book(self, book_id: str, options: Dict[str, Any] = None):
        """Process a book through the full ingest pipeline."""
        start_time = time.time()
        db = SessionLocal()
        
        try:
            # Get book
            book = db.query(Book).filter(Book.book_id == book_id).first()
            if not book:
                raise ValueError(f"Book {book_id} not found")
            
            options = options or {}
            
            # Step 1: Extract text
            book.ingest_status = "parsing"
            db.commit()
            
            print(f"[{book_id}] Step 1: Extracting text...")
            file_content = await self.storage_service.get_file(book.file_path)
            
            # Decrypt if needed
            if book.file_path.endswith(".encrypted"):
                from app.services.encryption import EncryptionService
                encryption_service = EncryptionService()
                file_content = await encryption_service.decrypt_file(book.file_path)
            
            # Save to temp file for processing (portable)
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{book.file_format}") as tf:
                tf.write(file_content)
                temp_path = tf.name
            temp_file = Path(temp_path)
            
            text = self.text_processor.extract_text(
                str(temp_file),
                book.file_format
            )
            text = self.text_processor.normalize_text(text)
            
            # Clean up temp file
            try:
                temp_file.unlink()
            except Exception:
                pass
            
            # Step 2: Detect chapters and chunk
            book.ingest_status = "chunking"
            db.commit()
            
            print(f"[{book_id}] Step 2: Chunking text...")
            chapter_markers = self.text_processor.detect_chapters(text)
            
            chunker = Chunker(
                chunk_size_words=options.get("chunk_size", settings.DEFAULT_CHUNK_SIZE),
                overlap_percent=options.get("overlap_percent", settings.DEFAULT_OVERLAP_PERCENT),
                prefer_chapter_boundaries=True
            )
            
            chunks = chunker.chunk_text(text, book_id, chapter_markers)
            
            # Save chunks to database
            for chunk in chunks:
                chunk_record = Chunk(
                    chunk_id=chunk.chunk_id,
                    book_id=book_id,
                    start_loc=chunk.start_loc,
                    end_loc=chunk.end_loc,
                    chapter_number=chunk.chapter_number,
                    excerpt_hint=chunk.excerpt_hint,
                    token_estimate=chunk.token_estimate,
                    chunk_text=chunk.chunk_text
                )
                db.add(chunk_record)
            
            db.commit()
            print(f"[{book_id}] Created {len(chunks)} chunks")
            
            # Step 3: Generate book profile using ingest prompt
            print(f"[{book_id}] Step 3: Generating book profile...")
            book_profile = await self._generate_book_profile(book_id, text, chunks)
            
            # Step 4: Generate embeddings
            book.ingest_status = "embedding"
            db.commit()
            
            print(f"[{book_id}] Step 4: Generating embeddings...")
            await self.embedding_service.generate_and_index_embeddings(
                book_id=book_id,
                chunks=chunks
            )
            
            # Step 5: Update book record
            book.ingest_status = "ready"
            book.book_profile = book_profile
            book.total_words = len(text.split())
            db.commit()
            
            duration = time.time() - start_time
            ingest_duration_seconds.labels(book_id=book_id, status="success").observe(duration)
            
            print(f"[{book_id}] Ingest complete in {duration:.2f}s")
            
        except Exception as e:
            book.ingest_status = "error"
            db.commit()
            duration = time.time() - start_time
            ingest_duration_seconds.labels(book_id=book_id, status="error").observe(duration)
            print(f"[{book_id}] Ingest failed: {e}")
            raise
        finally:
            db.close()
    
    async def _generate_book_profile(
        self,
        book_id: str,
        text: str,
        chunks: list
    ) -> Dict[str, Any]:
        """Generate book profile using LLM."""
        # Load master ingest prompt
        prompt_path = Path("master_ingest_prompt.txt")
        if not prompt_path.exists():
            # Try relative to backend
            prompt_path = Path("../master_ingest_prompt.txt")
        
        if not prompt_path.exists():
            raise FileNotFoundError("master_ingest_prompt.txt not found")
        
        master_prompt = prompt_path.read_text(encoding='utf-8')
        
        # Truncate text if too long (keep first 50k chars for profile generation)
        text_sample = text[:50000] if len(text) > 50000 else text
        
        # Call LLM
        if settings.DEFAULT_LLM_PROVIDER == "openai":
            import openai
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            
            response = client.chat.completions.create(
                model=settings.DEFAULT_LLM_MODEL,
                messages=[
                    {"role": "system", "content": master_prompt},
                    {"role": "user", "content": f"Process this book:\n\n{text_sample}"}
                ],
                temperature=0.1,
                max_tokens=16000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.DEFAULT_LLM_PROVIDER}")
