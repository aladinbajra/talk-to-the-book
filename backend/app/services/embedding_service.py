"""
Embedding service for generating and managing embeddings.
"""

import asyncio
import json
from functools import lru_cache
from pathlib import Path
from threading import Lock
from typing import List

import faiss
import numpy as np

from app.core.config import settings
from app.services.chunker import Chunk


@lru_cache(maxsize=2)
def _get_model(name):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(name)


_model_lock = Lock()


class EmbeddingService:
    """Lazy, process-cached embedding models and normalized vector indices."""

    def __init__(self):
        self.model = None

    def _load_model(self):
        if self.model is None:
            with _model_lock:
                self.model = _get_model(settings.EMBEDDING_MODEL)
        return self.model

    async def generate_and_index_embeddings(self, book_id: str, chunks: List[Chunk]):
        """Generate embeddings for chunks and create FAISS index."""
        # Extract chunk texts
        chunk_texts = [chunk.chunk_text for chunk in chunks]
        chunk_ids = [chunk.chunk_id for chunk in chunks]

        # Generate embeddings
        print(f"Generating embeddings for {len(chunk_texts)} chunks...")
        embeddings = await asyncio.to_thread(
            lambda: self._load_model().encode(
                chunk_texts,
                batch_size=settings.EMBEDDING_BATCH_SIZE,
                show_progress_bar=True,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
        )

        # Build FAISS index
        dimension = embeddings.shape[1]
        index = faiss.IndexHNSWFlat(dimension, 32, faiss.METRIC_INNER_PRODUCT)
        index.hnsw.efConstruction = 200
        index.hnsw.efSearch = 64

        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        index.add(embeddings)

        # Save index
        index_dir = Path(settings.FAISS_INDEX_PATH)
        index_dir.mkdir(parents=True, exist_ok=True)

        index_path = index_dir / f"{book_id}.faiss"
        metadata_path = index_dir / f"{book_id}_metadata.json"

        faiss.write_index(index, str(index_path))

        # Save metadata
        metadata = {
            "similarity_metric": "cosine",
            "book_id": book_id,
            "num_chunks": len(chunks),
            "embedding_dim": dimension,
            "model_name": settings.EMBEDDING_MODEL,
            "chunk_ids": chunk_ids,
        }

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Save embeddings
        embeddings_path = index_dir / f"{book_id}_embeddings.npz"
        np.savez_compressed(embeddings_path, embeddings=embeddings)

        print(f"OK Saved index and embeddings for {book_id}")

    def load_index(self, book_id: str):
        """Load FAISS index for a book."""
        index_dir = Path(settings.FAISS_INDEX_PATH)
        index_path = index_dir / f"{book_id}.faiss"
        metadata_path = index_dir / f"{book_id}_metadata.json"

        if not index_path.exists():
            raise FileNotFoundError(f"Index not found for book {book_id}")

        index = faiss.read_index(str(index_path))

        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        return index, metadata

    def encode_query(self, query: str) -> np.ndarray:
        """Encode a query into an embedding."""
        embedding = self._load_model().encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        )
        return embedding[0]
