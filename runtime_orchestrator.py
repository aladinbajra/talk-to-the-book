#!/usr/bin/env python3
"""
Runtime orchestrator for "Talk to the Book" Q&A system.

This script handles the complete flow:
1. Load book configuration and embeddings
2. Process user queries
3. Retrieve relevant chunks
4. Generate answers using LLM
5. Return structured responses
"""

import json
import argparse
import sys
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class RetrievedChunk:
    """Represents a retrieved chunk with metadata."""
    chunk_id: str
    chunk_text: str
    similarity_score: float
    chapter: int
    start_loc: str
    end_loc: str


@dataclass
class QueryResponse:
    """Structured response to a user query."""
    answer: str
    confidence: float
    source_chunk_ids: List[str]
    answer_type: str  # "factual", "interpretive", "summary", "unknown"
    retrieved_chunks: List[RetrievedChunk]


class BookOrchestrator:
    """Main orchestrator for book Q&A system."""
    
    def __init__(
        self,
        ingest_json_path: str,
        embeddings_path: str,
        index_path: str,
        chunks_jsonl_path: str
    ):
        """Initialize orchestrator with book data."""
        # Load ingest configuration
        print(f"Loading ingest config from: {ingest_json_path}")
        with open(ingest_json_path, 'r', encoding='utf-8') as f:
            self.ingest_data = json.load(f)
        
        self.book_id = self.ingest_data.get("book_id", "unknown")
        self.book_profile = self.ingest_data.get("book_profile", {})
        self.retrieval_config = self.ingest_data.get("retrieval_config", {})
        self.runtime_prompts = self.ingest_data.get("runtime_prompts", {})
        
        # Load embeddings and index
        print(f"Loading embeddings from: {embeddings_path}")
        from embedding_utils import load_embeddings, load_faiss_index
        self.embeddings, self.embeddings_metadata = load_embeddings(embeddings_path)
        self.index, self.index_metadata = load_faiss_index(index_path)
        
        # Load chunks metadata
        print(f"Loading chunks from: {chunks_jsonl_path}")
        self.chunks = {}
        with open(chunks_jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                chunk = json.loads(line)
                self.chunks[chunk["chunk_id"]] = chunk
        
        print(f"✓ Loaded {len(self.chunks)} chunks")
        
        # Load embedding model for query encoding
        model_name = self.retrieval_config.get("recommended_embedding_model", "sentence-transformers/all-mpnet-base-v2")
        from embedding_utils import load_embedding_model
        self.embedding_model = load_embedding_model(model_name)
        
        # Initialize conversation history
        self.conversation_history: List[Dict[str, str]] = []
    
    def encode_query(self, query: str) -> np.ndarray:
        """Encode user query into embedding."""
        import numpy as np
        embedding = self.embedding_model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        return embedding[0]
    
    def retrieve_chunks(
        self,
        query: str,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None
    ) -> List[RetrievedChunk]:
        """Retrieve relevant chunks for a query."""
        if top_k is None:
            top_k = self.retrieval_config.get("top_k_retrieval_default", 6)
        if similarity_threshold is None:
            similarity_threshold = self.retrieval_config.get("similarity_threshold_default", 0.12)
        
        # Encode query
        query_embedding = self.encode_query(query)
        
        # Search index
        from embedding_utils import search_similar
        results = search_similar(query_embedding, self.index, top_k=top_k, similarity_threshold=similarity_threshold)
        
        # Build RetrievedChunk objects
        retrieved = []
        for idx, similarity in results:
            chunk_id = self.embeddings_metadata["chunk_ids"][idx]
            chunk_data = self.chunks[chunk_id]
            
            retrieved.append(RetrievedChunk(
                chunk_id=chunk_id,
                chunk_text=chunk_data["chunk_text"],
                similarity_score=similarity,
                chapter=chunk_data.get("chapter", 0),
                start_loc=chunk_data.get("start_loc", ""),
                end_loc=chunk_data.get("end_loc", "")
            ))
        
        return retrieved
    
    def format_user_prompt(
        self,
        query: str,
        retrieved_chunks: List[RetrievedChunk]
    ) -> str:
        """Format user prompt using template."""
        template = self.runtime_prompts.get("user_prompt_template", "")
        
        # Format chunks
        chunks_text = ""
        for i, chunk in enumerate(retrieved_chunks):
            chunks_text += f"\n--- Chunk {i+1} (ID: {chunk.chunk_id}, Similarity: {chunk.similarity_score:.3f}) ---\n"
            chunks_text += chunk.chunk_text + "\n"
        
        # Format conversation history
        history_text = ""
        if self.conversation_history:
            for turn in self.conversation_history[-5:]:  # Last 5 turns
                history_text += f"User: {turn.get('user', '')}\n"
                history_text += f"Assistant: {turn.get('assistant', '')}\n\n"
        
        # Fill template
        prompt = template.replace("{BOOK_ID}", self.book_id)
        prompt = prompt.replace("{BOOK_PROFILE}", json.dumps(self.book_profile, indent=2))
        prompt = prompt.replace("{CHUNKS}", chunks_text)
        prompt = prompt.replace("{HISTORY}", history_text)
        prompt = prompt.replace("{QUESTION}", query)
        
        return prompt
    
    def generate_answer(
        self,
        query: str,
        retrieved_chunks: List[RetrievedChunk],
        api_type: str = "openai",
        **kwargs
    ) -> Dict:
        """Generate answer using LLM."""
        system_prompt = self.runtime_prompts.get("system_prompt", "")
        user_prompt = self.format_user_prompt(query, retrieved_chunks)
        
        if api_type == "openai":
            try:
                import openai
                client = openai.OpenAI(api_key=kwargs.get('api_key'))
                
                response = client.chat.completions.create(
                    model=kwargs.get('model', 'gpt-4-turbo-preview'),
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=kwargs.get('temperature', 0.3),
                    response_format={"type": "json_object"}
                )
                
                result = json.loads(response.choices[0].message.content)
                return result
                
            except Exception as e:
                raise RuntimeError(f"OpenAI API error: {e}")
        else:
            raise NotImplementedError(f"API type {api_type} not yet implemented")
    
    def query(
        self,
        user_query: str,
        api_type: str = "openai",
        **api_kwargs
    ) -> QueryResponse:
        """Process a user query and return response."""
        # Retrieve chunks
        retrieved_chunks = self.retrieve_chunks(user_query)
        
        if not retrieved_chunks:
            # No relevant chunks found
            return QueryResponse(
                answer="UNKNOWN_IN_BOOK",
                confidence=0.0,
                source_chunk_ids=[],
                answer_type="unknown",
                retrieved_chunks=[]
            )
        
        # Generate answer
        llm_response = self.generate_answer(user_query, retrieved_chunks, api_type, **api_kwargs)
        
        # Parse response
        answer = llm_response.get("answer", "UNKNOWN_IN_BOOK")
        confidence = llm_response.get("confidence", 0.5)
        source_chunk_ids = llm_response.get("source_chunk_ids", [chunk.chunk_id for chunk in retrieved_chunks])
        answer_type = llm_response.get("answer_type", "factual")
        
        # Update conversation history
        self.conversation_history.append({
            "user": user_query,
            "assistant": answer
        })
        
        return QueryResponse(
            answer=answer,
            confidence=confidence,
            source_chunk_ids=source_chunk_ids,
            answer_type=answer_type,
            retrieved_chunks=retrieved_chunks
        )
    
    def reset_conversation(self):
        """Reset conversation history."""
        self.conversation_history = []


def main():
    parser = argparse.ArgumentParser(
        description="Runtime orchestrator for Talk to the Book",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "ingest_json",
        help="Path to ingest JSON file"
    )
    
    parser.add_argument(
        "--embeddings",
        required=True,
        help="Path to embeddings NPZ file"
    )
    
    parser.add_argument(
        "--index",
        required=True,
        help="Path to FAISS index file"
    )
    
    parser.add_argument(
        "--chunks",
        required=True,
        help="Path to chunks JSONL file"
    )
    
    parser.add_argument(
        "--query", "-q",
        help="Single query to process (interactive mode if not provided)"
    )
    
    parser.add_argument(
        "--api",
        choices=["openai"],
        default="openai",
        help="LLM API to use"
    )
    
    parser.add_argument(
        "--api-key",
        help="API key (or set OPENAI_API_KEY env var)"
    )
    
    parser.add_argument(
        "--model",
        help="Model name"
    )
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = BookOrchestrator(
        args.ingest_json,
        args.embeddings,
        args.index,
        args.chunks
    )
    
    # Get API key
    api_key = args.api_key
    if not api_key:
        import os
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("Error: API key required", file=sys.stderr)
        sys.exit(1)
    
    api_kwargs = {
        "api_key": api_key,
        "model": args.model
    }
    
    # Process query
    if args.query:
        response = orchestrator.query(args.query, args.api, **api_kwargs)
        print("\n" + "="*60)
        print("RESPONSE")
        print("="*60)
        print(f"Answer: {response.answer}")
        print(f"Confidence: {response.confidence:.2f}")
        print(f"Answer Type: {response.answer_type}")
        print(f"Source Chunks: {', '.join(response.source_chunk_ids)}")
        print("="*60)
    else:
        # Interactive mode
        print("\n" + "="*60)
        print("Talk to the Book - Interactive Mode")
        print("Type 'quit' or 'exit' to exit")
        print("Type 'reset' to clear conversation history")
        print("="*60 + "\n")
        
        while True:
            try:
                query = input("You: ").strip()
                if not query:
                    continue
                
                if query.lower() in ['quit', 'exit']:
                    break
                
                if query.lower() == 'reset':
                    orchestrator.reset_conversation()
                    print("Conversation history cleared.\n")
                    continue
                
                response = orchestrator.query(query, args.api, **api_kwargs)
                
                print(f"\nAssistant: {response.answer}")
                print(f"[Confidence: {response.confidence:.2f}, Type: {response.answer_type}]")
                if response.source_chunk_ids:
                    print(f"[Sources: {len(response.source_chunk_ids)} chunks]\n")
                
            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}\n", file=sys.stderr)


if __name__ == "__main__":
    main()
