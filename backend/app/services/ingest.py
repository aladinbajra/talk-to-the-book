"""
Ingest service for processing books.
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

import numpy as np

from app.core.config import settings
from app.core.metrics import ingest_duration_seconds
from app.db.database import SessionLocal
from app.db.models import Book, Chunk
from app.services.chunker import Chunker
from app.services.embedding_service import EmbeddingService
from app.services.storage import StorageService
from app.services.text_processor import TextProcessor


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
        book = None

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
                file_content = encryption_service.decrypt_bytes(file_content)

            # Portable temp files, removed even when parsing fails.
            def extract():
                with tempfile.TemporaryDirectory(prefix="book-ingest-") as directory:
                    temp_file = Path(directory) / f"source.{book.file_format}"
                    temp_file.write_bytes(file_content)
                    return self.text_processor.extract_text(
                        str(temp_file), book.file_format
                    )

            text = self.text_processor.normalize_text(await asyncio.to_thread(extract))
            if not text.strip():
                raise ValueError("No readable text was found in the book")

            # Step 2: Detect chapters and chunk
            book.ingest_status = "chunking"
            db.commit()

            print(f"[{book_id}] Step 2: Chunking text...")
            chapter_markers = self.text_processor.detect_chapters(text)

            chunker = Chunker(
                chunk_size_words=options.get("chunk_size", settings.DEFAULT_CHUNK_SIZE),
                overlap_percent=options.get(
                    "overlap_percent", settings.DEFAULT_OVERLAP_PERCENT
                ),
                prefer_chapter_boundaries=True,
            )

            chunks = chunker.chunk_text(text, book_id, chapter_markers)

            # Retries replace their own prior chunks rather than colliding on stable ids.
            db.query(Chunk).filter(Chunk.book_id == book_id).delete(
                synchronize_session=False
            )
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
                    chunk_text=chunk.chunk_text,
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
                book_id=book_id, chunks=chunks
            )

            # Step 5: Update book record
            book.ingest_status = "ready"
            book.book_profile = book_profile
            metadata = book_profile.get("book_metadata", {})
            book.title = metadata.get("title") or book.title
            book.author = metadata.get("author") or book.author
            book.language = metadata.get("language") or book.language
            book.total_words = len(text.split())
            db.commit()

            duration = time.time() - start_time
            ingest_duration_seconds.labels(book_id=book_id, status="success").observe(
                duration
            )

            print(f"[{book_id}] Ingest complete in {duration:.2f}s")

        except Exception:
            db.rollback()
            failed_book = db.query(Book).filter(Book.book_id == book_id).first()
            if failed_book is not None:
                failed_book.ingest_status = "error"
                db.commit()
            ingest_duration_seconds.labels(book_id=book_id, status="error").observe(
                time.time() - start_time
            )
            logging.getLogger(__name__).exception("Book ingestion failed: %s", book_id)

        finally:
            db.close()

    async def _generate_book_profile(
        self, book_id: str, text: str, chunks: list
    ) -> Dict[str, Any]:
        """Generate book profile using LLM."""
        # Load master ingest prompt
        candidates = [
            Path(__file__).resolve().parents[3] / "master_ingest_prompt.txt",
            Path(__file__).resolve().parents[2] / "master_ingest_prompt.txt",
        ]
        prompt_path = next((path for path in candidates if path.is_file()), None)
        if prompt_path is None:
            raise FileNotFoundError("master_ingest_prompt.txt not found")

        master_prompt = prompt_path.read_text(encoding="utf-8")

        # Truncate text if too long (keep first 50k chars for profile generation)
        text_sample = text[:50000] if len(text) > 50000 else text

        # Call LLM
        if settings.DEFAULT_LLM_PROVIDER == "openai":
            import openai

            client = openai.AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=settings.LLM_TIMEOUT_SECONDS,
                max_retries=1,
            )

            async with client:
                response = await client.chat.completions.create(
                    model=settings.DEFAULT_LLM_MODEL,
                    messages=[
                        {"role": "system", "content": master_prompt},
                        {
                            "role": "user",
                            "content": f"Process this book:\n\n{text_sample}",
                        },
                    ],
                    temperature=0.1,
                    max_tokens=16000,
                    response_format={"type": "json_object"},
                )

            result = json.loads(response.choices[0].message.content)
            return result

        else:
            raise ValueError(
                f"Unsupported LLM provider: {settings.DEFAULT_LLM_PROVIDER}"
            )
