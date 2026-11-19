"""
Query service for processing user queries.
"""

import asyncio
import json
import math
import time
from functools import lru_cache
from typing import Any, Dict, List

import faiss
import numpy as np
import openai

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import Book, Chunk
from app.services.embedding_service import EmbeddingService


@lru_cache(maxsize=1)
def _get_reranker(name):
    from sentence_transformers import CrossEncoder

    return CrossEncoder(name)


class QueryService:
    """Service for processing queries."""

    def __init__(self):
        self.embedding_service = EmbeddingService()

    async def process_query(
        self,
        book_id: str,
        question: str,
        history: List[Dict[str, str]] = None,
        options: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """Process a query and return response."""
        db = SessionLocal()

        try:
            # Get book
            book = db.query(Book).filter(Book.book_id == book_id).first()
            if not book:
                raise ValueError(f"Book {book_id} not found")

            if not book.book_profile:
                raise ValueError("Book profile not available")

            # Load index
            index, metadata = self.embedding_service.load_index(book_id)
            chunk_ids = metadata["chunk_ids"]

            # Encode query
            query_embedding = await asyncio.to_thread(
                self.embedding_service.encode_query, question
            )
            query_embedding = query_embedding.reshape(1, -1)
            faiss.normalize_L2(query_embedding)

            # Retrieve chunks
            top_k = (
                options.get("top_k", settings.TOP_K_RETRIEVAL)
                if options
                else settings.TOP_K_RETRIEVAL
            )

            # First pass: get top 200
            k_search = min(200, len(chunk_ids))
            distances, indices = index.search(query_embedding, k_search)

            # Filter by similarity threshold
            retrieved_chunks = []
            for idx, dist in zip(indices[0], distances[0]):
                if idx < 0 or idx >= len(chunk_ids) or not math.isfinite(float(dist)):
                    continue

                similarity = (
                    float(dist)
                    if index.metric_type == faiss.METRIC_INNER_PRODUCT
                    else 1.0 - float(dist) / 2.0
                )
                if similarity >= settings.SIMILARITY_THRESHOLD:
                    chunk_id = chunk_ids[idx]
                    chunk = (
                        db.query(Chunk)
                        .filter(Chunk.chunk_id == chunk_id, Chunk.book_id == book_id)
                        .first()
                    )
                    if chunk:
                        retrieved_chunks.append(
                            {
                                "chunk_id": chunk_id,
                                "chunk_text": chunk.chunk_text,
                                "similarity": float(similarity),
                                "chapter": chunk.chapter_number,
                                "start_loc": chunk.start_loc,
                                "end_loc": chunk.end_loc,
                            }
                        )

            if not retrieved_chunks:
                # No relevant chunks found
                return {
                    "answer": "UNKNOWN IN BOOK",
                    "confidence": 0.0,
                    "style_score": "unknown",
                    "sources": [],
                    "explanation": "No relevant content found in the book.",
                    "notes": "UNKNOWN IN BOOK",
                }

            # Rerank if enabled
            if settings.RERANK_ENABLED and len(retrieved_chunks) > top_k:
                retrieved_chunks = await self._rerank(question, retrieved_chunks)

            # Take top K
            final_chunks = retrieved_chunks[:top_k]

            # Generate answer
            response = await self._generate_answer(
                book_id=book_id,
                question=question,
                chunks=final_chunks,
                book_profile=book.book_profile,
                history=history or [],
                options=options or {},
            )

            return response

        finally:
            db.close()

    async def _rerank(self, question: str, chunks: List[Dict]) -> List[Dict]:
        """Rerank chunks using cross-encoder."""
        try:
            model = await asyncio.to_thread(_get_reranker, settings.RERANK_MODEL)

            # Prepare pairs
            pairs = [[question, chunk["chunk_text"]] for chunk in chunks]

            # Score
            scores = await asyncio.to_thread(model.predict, pairs)

            # Sort by score
            chunk_scores = list(zip(chunks, scores))
            chunk_scores.sort(key=lambda x: x[1], reverse=True)

            return [chunk for chunk, score in chunk_scores]

        except Exception as e:
            print(f"Reranking failed: {e}, using original order")
            return chunks

    async def _generate_answer(
        self,
        book_id: str,
        question: str,
        chunks: List[Dict],
        book_profile: Dict,
        history: List[Dict],
        options: Dict,
    ) -> Dict[str, Any]:
        """Generate answer using LLM."""
        # Build system prompt
        system_prompt = self._build_system_prompt(book_profile)

        # Build user prompt
        chunks_text = "\n\n".join(
            [
                f"--- Chunk {i+1} (ID: {ch['chunk_id']}, Similarity: {ch['similarity']:.3f}) ---\n{ch['chunk_text']}"
                for i, ch in enumerate(chunks)
            ]
        )

        history_text = ""
        if history:
            for turn in history[-5:]:  # Last 5 turns
                history_text += f"User: {turn.get('user', '')}\n"
                history_text += f"Assistant: {turn.get('assistant', '')}\n\n"

        user_prompt = f"""BOOK_ID: {book_id}
BOOK_PROFILE: {json.dumps(book_profile.get('book_profile', {}), indent=2)}

RETRIEVED_CHUNKS:
{chunks_text}

CONVERSATION_HISTORY:
{history_text}

USER_QUESTION: {question}"""

        # Call LLM
        client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            max_retries=1,
        )

        async with client:
            response = await client.chat.completions.create(
                model=settings.DEFAULT_LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

        result = json.loads(response.choices[0].message.content)

        return self.validate_answer(result, chunks)

    @staticmethod
    def validate_answer(result, chunks):
        evidence = {chunk["chunk_id"]: chunk for chunk in chunks}
        sources = result.get("sources")
        answer = result.get("answer")
        confidence = result.get("confidence", 0.0)
        valid = (
            isinstance(sources, list)
            and bool(sources)
            and all(
                isinstance(source, str) and source in evidence for source in sources
            )
        )
        if (
            not valid
            or not isinstance(answer, str)
            or not answer.strip()
            or answer.strip() == "UNKNOWN IN BOOK"
        ):
            return {
                "answer": "UNKNOWN IN BOOK",
                "confidence": 0.0,
                "style_score": "unknown",
                "sources": [],
                "source_details": [],
                "explanation": "No supported answer was found in the retrieved book passages.",
                "notes": "UNKNOWN IN BOOK",
            }
        if not isinstance(confidence, (int, float)) or not math.isfinite(confidence):
            confidence = 0.0
        sources = list(dict.fromkeys(sources))
        return {
            "answer": answer.strip(),
            "confidence": max(0.0, min(1.0, confidence)),
            "style_score": str(result.get("style_score", "factual")),
            "sources": sources,
            "source_details": [
                {
                    "chunk_id": source,
                    "excerpt": evidence[source]["chunk_text"][:800],
                    "chapter": evidence[source].get("chapter"),
                    "start_loc": evidence[source].get("start_loc"),
                    "end_loc": evidence[source].get("end_loc"),
                }
                for source in sources
            ],
            "explanation": str(
                result.get("explanation", "Based on the cited book passages.")
            ),
            "notes": result.get("notes"),
        }

    def _build_system_prompt(self, book_profile: Dict) -> str:
        """Build system prompt from book profile."""
        profile = book_profile.get("book_profile", {})
        voice = book_profile.get("persona_and_voice", {})

        prompt = f"""You are a helpful assistant that answers questions about a specific book. You MUST answer ONLY using information from the provided book chunks. If the answer is not in the book, respond with the exact JSON: {{"answer": "UNKNOWN IN BOOK", "confidence": 0.0, "style_score": "unknown", "sources": [], "explanation": "The book does not contain information about this topic.", "notes": "UNKNOWN IN BOOK"}}.

Book Voice Profile:
{json.dumps(voice, indent=2)}

Maintain the book's voice and writing style in your responses. Output your answer as JSON with this exact schema:
{{
  "answer": "<string>",
  "confidence": <float 0.00-1.00>,
  "style_score": "<literal|interpretive|summary|concise|detailed>",
  "sources": ["chunk_id", ...],
  "explanation": "<1-2 sentence provenance>",
  "notes": "<optional flags>"
}}

Rules:
- Answer only from provided chunks
- If confidence < 0.35, prefix answer with "UNSURE: "
- If no evidence, return UNKNOWN IN BOOK JSON
- Do not quote more than 25 words verbatim
- Include chunk_ids used in sources array"""

        return prompt
