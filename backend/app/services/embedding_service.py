"""
Embedding service for generating and managing embeddings.
"""
import numpy as np
from pathlib import Path
from typing import List
import json

from app.services.chunker import Chunk
from app.core.config import settings
from sentence_transformers import SentenceTransformer
import faiss


class EmbeddingService:
    """Service for generating embeddings and managing vector indices."""
    
    def __init__(self):
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load embedding model."""
        print(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        print("✓ Model loaded")
    
    async def generate_and_index_embeddings(
        self,
        book_id: str,
        chunks: List[Chunk]
    ):
        """Generate embeddings for chunks and create FAISS index."""
        # Extract chunk texts
        chunk_texts = [chunk.chunk_text for chunk in chunks]
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        
        # Generate embeddings
        print(f"Generating embeddings for {len(chunk_texts)} chunks...")
        embeddings = self.model.encode(
            chunk_texts,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        # Build FAISS index
        dimension = embeddings.shape[1]
        index = faiss.IndexHNSWFlat(dimension, 32)
        index.hnsw.efConstruction = 200
        index.hnsw.efSearch = 64
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
        
        # Save index
        index_dir = Path(settings.FAISS_INDEX_PATH)
        index_dir.mkdir(parents=True, exist_ok=True)

        embeddings_dir = Path(settings.EMBEDDINGS_PATH)
        embeddings_dir.mkdir(parents=True, exist_ok=True)

        index_path = index_dir / f"{book_id}.faiss"
        metadata_path = index_dir / f"{book_id}_metadata.json"
        
        faiss.write_index(index, str(index_path))
        
        # Save metadata
        metadata = {
            "book_id": book_id,
            "num_chunks": len(chunks),
            "embedding_dim": dimension,
            "model_name": settings.EMBEDDING_MODEL,
            "chunk_ids": chunk_ids
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Save embeddings (separate path)
        embeddings_path = embeddings_dir / f"{book_id}_embeddings.npz"
        np.savez_compressed(embeddings_path, embeddings=embeddings)
        
        print(f"✓ Saved index and embeddings for {book_id}")
    
    def load_index(self, book_id: str):
        """Load FAISS index for a book."""
        index_dir = Path(settings.FAISS_INDEX_PATH)
        index_path = index_dir / f"{book_id}.faiss"
        metadata_path = index_dir / f"{book_id}_metadata.json"
        
        if not index_path.exists():
            raise FileNotFoundError(f"Index not found for book {book_id}")
        
        index = faiss.read_index(str(index_path))
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        return index, metadata
    
    def encode_query(self, query: str) -> np.ndarray:
        """Encode a query into an embedding."""
        embedding = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embedding[0]
