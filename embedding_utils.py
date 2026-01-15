#!/usr/bin/env python3
"""
Utilities for generating embeddings and managing vector indices.
"""

import numpy as np
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple


def load_embedding_model(model_name: str = "sentence-transformers/all-mpnet-base-v2"):
    """
    Load embedding model.
    
    Args:
        model_name: Name of the model to load
    
    Returns:
        Loaded model
    """
    try:
        from sentence_transformers import SentenceTransformer
        print(f"Loading embedding model: {model_name}")
        model = SentenceTransformer(model_name)
        print("✓ Model loaded successfully")
        return model
    except ImportError:
        raise ImportError("sentence-transformers not installed. Install with: pip install sentence-transformers")
    except Exception as e:
        raise RuntimeError(f"Error loading model: {e}")


def generate_embeddings(
    texts: List[str],
    model,
    batch_size: int = 32,
    show_progress: bool = True
) -> np.ndarray:
    """
    Generate embeddings for a list of texts.
    
    Args:
        texts: List of text strings to embed
        model: Loaded embedding model
        batch_size: Batch size for processing
        show_progress: Whether to show progress bar
    
    Returns:
        Numpy array of embeddings (n_texts, embedding_dim)
    """
    print(f"Generating embeddings for {len(texts)} texts...")
    
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        convert_to_numpy=True,
        normalize_embeddings=True  # Normalize for cosine similarity
    )
    
    print(f"✓ Generated embeddings shape: {embeddings.shape}")
    return embeddings


def save_embeddings(embeddings: np.ndarray, output_path: str, metadata: Dict = None):
    """
    Save embeddings to NPZ file with optional metadata.
    
    Args:
        embeddings: Numpy array of embeddings
        output_path: Output file path
        metadata: Optional metadata dictionary
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    save_dict = {"embeddings": embeddings}
    if metadata:
        save_dict["metadata"] = metadata
    
    np.savez_compressed(output_file, **save_dict)
    print(f"✓ Saved embeddings to: {output_file}")


def load_embeddings(npz_path: str) -> Tuple[np.ndarray, Optional[Dict]]:
    """
    Load embeddings from NPZ file.
    
    Args:
        npz_path: Path to NPZ file
    
    Returns:
        Tuple of (embeddings array, metadata dict or None)
    """
    data = np.load(npz_path, allow_pickle=True)
    embeddings = data["embeddings"]
    metadata = data.get("metadata", None)
    
    if metadata is not None and isinstance(metadata, np.ndarray):
        metadata = metadata.item()
    
    return embeddings, metadata


def build_faiss_index(
    embeddings: np.ndarray,
    index_type: str = "HNSW",
    M: int = 32,
    ef_construction: int = 200,
    ef_search: int = 50
):
    """
    Build FAISS index from embeddings.
    
    Args:
        embeddings: Numpy array of embeddings
        index_type: Type of index ('HNSW', 'IVF', 'Flat')
        M: HNSW parameter M (number of connections)
        ef_construction: HNSW parameter ef_construction
        ef_search: HNSW parameter ef_search
    
    Returns:
        FAISS index object
    """
    try:
        import faiss
    except ImportError:
        raise ImportError("faiss-cpu or faiss-gpu not installed. Install with: pip install faiss-cpu")
    
    dimension = embeddings.shape[1]
    
    if index_type == "HNSW":
        # HNSW index for approximate nearest neighbor search
        index = faiss.IndexHNSWFlat(dimension, M)
        index.hnsw.efConstruction = ef_construction
        index.hnsw.efSearch = ef_search
    elif index_type == "IVF":
        # IVF index with HNSW quantizer
        quantizer = faiss.IndexHNSWFlat(dimension, M)
        nlist = min(100, len(embeddings) // 100)  # Number of clusters
        index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
        index.train(embeddings)
        index.nprobe = 10
    else:  # Flat
        # Exact search (brute force)
        index = faiss.IndexFlatL2(dimension)
    
    # Normalize embeddings if using cosine similarity
    if index_type != "Flat":
        faiss.normalize_L2(embeddings)
    
    index.add(embeddings)
    
    print(f"✓ Built FAISS {index_type} index with {index.ntotal} vectors")
    return index


def save_faiss_index(index, output_path: str, metadata: Dict = None):
    """Save FAISS index to file."""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    import faiss
    faiss.write_index(index, str(output_file))
    
    if metadata:
        metadata_path = output_file.with_suffix('.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        print(f"✓ Saved metadata to: {metadata_path}")
    
    print(f"✓ Saved FAISS index to: {output_file}")


def load_faiss_index(index_path: str) -> Tuple:
    """Load FAISS index from file."""
    import faiss
    index = faiss.read_index(str(index_path))
    
    # Try to load metadata
    metadata_path = Path(index_path).with_suffix('.json')
    metadata = None
    if metadata_path.exists():
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    
    return index, metadata


def search_similar(
    query_embedding: np.ndarray,
    index,
    top_k: int = 6,
    similarity_threshold: float = 0.12
) -> List[Tuple[int, float]]:
    """
    Search for similar vectors in FAISS index.
    
    Args:
        query_embedding: Query embedding vector (1, dim)
        index: FAISS index
        top_k: Number of results to return
        similarity_threshold: Minimum similarity threshold (for cosine, this is distance threshold)
    
    Returns:
        List of (index, similarity_score) tuples
    """
    import faiss
    
    # Normalize query embedding for cosine similarity
    query_embedding = query_embedding.reshape(1, -1)
    faiss.normalize_L2(query_embedding)
    
    # Search
    distances, indices = index.search(query_embedding, top_k)
    
    # Convert distances to similarities (for cosine: similarity = 1 - distance)
    results = []
    for i, (idx, dist) in enumerate(zip(indices[0], distances[0])):
        if idx == -1:  # FAISS returns -1 for invalid results
            continue
        
        similarity = 1.0 - dist  # For cosine distance
        if similarity >= similarity_threshold:
            results.append((int(idx), float(similarity)))
    
    return results


def process_chunks_to_embeddings(
    chunks_jsonl: str,
    ingest_json: str,
    output_dir: str = "embeddings",
    model_name: str = None
) -> Tuple[str, str]:
    """
    Process chunks JSONL file and generate embeddings + FAISS index.
    
    Args:
        chunks_jsonl: Path to chunks JSONL file
        ingest_json: Path to ingest JSON file (for config)
        output_dir: Output directory
        model_name: Override embedding model name
    
    Returns:
        Tuple of (embeddings_path, index_path)
    """
    # Load ingest config
    with open(ingest_json, 'r', encoding='utf-8') as f:
        ingest_data = json.load(f)
    
    book_id = ingest_data.get("book_id", "unknown")
    retrieval_config = ingest_data.get("retrieval_config", {})
    
    # Determine model
    if model_name is None:
        model_name = retrieval_config.get("recommended_embedding_model", "sentence-transformers/all-mpnet-base-v2")
    
    batch_size = retrieval_config.get("embedding_batch_size", 32)
    
    # Load chunks
    print(f"Loading chunks from: {chunks_jsonl}")
    chunks = []
    chunk_texts = []
    with open(chunks_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            chunk = json.loads(line)
            chunks.append(chunk)
            chunk_texts.append(chunk["chunk_text"])
    
    print(f"✓ Loaded {len(chunks)} chunks")
    
    # Generate embeddings
    model = load_embedding_model(model_name)
    embeddings = generate_embeddings(chunk_texts, model, batch_size=batch_size)
    
    # Save embeddings
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    embeddings_path = output_path / f"{book_id}_embeddings.npz"
    metadata = {
        "book_id": book_id,
        "num_chunks": len(chunks),
        "embedding_dim": embeddings.shape[1],
        "model_name": model_name,
        "chunk_ids": [chunk["chunk_id"] for chunk in chunks]
    }
    save_embeddings(embeddings, str(embeddings_path), metadata)
    
    # Build FAISS index
    index_config = retrieval_config.get("index_parameters", {})
    M = index_config.get("M", 32)
    ef_construction = index_config.get("ef_construction", 200)
    
    index = build_faiss_index(embeddings, M=M, ef_construction=ef_construction)
    
    index_path = output_path / f"{book_id}_index.faiss"
    save_faiss_index(index, str(index_path), metadata)
    
    return str(embeddings_path), str(index_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate embeddings and FAISS index from chunks",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "chunks_jsonl",
        help="Path to chunks JSONL file"
    )
    
    parser.add_argument(
        "ingest_json",
        help="Path to ingest JSON file"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        default="embeddings",
        help="Output directory (default: embeddings)"
    )
    
    parser.add_argument(
        "--model",
        help="Override embedding model name"
    )
    
    args = parser.parse_args()
    
    embeddings_path, index_path = process_chunks_to_embeddings(
        args.chunks_jsonl,
        args.ingest_json,
        args.output_dir,
        args.model
    )
    
    print("\n" + "="*60)
    print("EMBEDDING GENERATION COMPLETE")
    print("="*60)
    print(f"Embeddings: {embeddings_path}")
    print(f"FAISS Index: {index_path}")
    print("="*60)


if __name__ == "__main__":
    main()
