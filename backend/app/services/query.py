"""
Query service for processing user queries.

Hardening goals:
- source-only enforcement with fallback
- deterministic caching
- PII redaction (emails/phones/SSN-like)
- validator gate (schema + provenance heuristics)
- metrics for retrieval/rerank/generation/cache
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import openai

from app.core.config import settings
from app.core.metrics import (
    cache_hit_counter,
    cache_miss_counter,
    generation_latency_seconds,
    retrieval_candidates_gauge,
    rerank_latency_seconds,
)
from app.core.response_validator import FALLBACK_RESPONSE, ResponseValidator
from app.db.database import SessionLocal
from app.db.models import Book, Chunk
from app.services.cache import CacheService
from app.services.embedding_service import EmbeddingService


class QueryService:
    """Service for processing queries."""

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.cache = CacheService(
            redis_url=settings.REDIS_URL or None,
            ttl_seconds=settings.CACHE_TTL_SECONDS,
        )
        self.validator = ResponseValidator()
        self._runtime_prompt = self._load_runtime_prompt()
        self._rerank_model = None  # lazy-load and reuse

    async def process_query(
        self,
        book_id: str,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process a query and return response."""
        db = SessionLocal()
        try:
            history = history or []
            options = options or {}

            # Cache first (deterministic hash)
            qhash = self.cache.make_query_hash(book_id, question, history, options)
            cached = self.cache.get(book_id, qhash)
            if cached:
                cache_hit_counter.labels(book_id=book_id).inc()
                return cached
            cache_miss_counter.labels(book_id=book_id).inc()

            # Book
            book = db.query(Book).filter(Book.book_id == book_id).first()
            if not book:
                raise ValueError(f"Book {book_id} not found")
            if not book.book_profile:
                raise ValueError("Book profile not available")

            # Index
            index, metadata = self.embedding_service.load_index(book_id)
            chunk_ids = metadata["chunk_ids"]

            # Query embedding
            query_embedding = self.embedding_service.encode_query(question).reshape(1, -1)
            faiss.normalize_L2(query_embedding)

            # Retrieval
            top_k = int(options.get("top_k", settings.TOP_K_RETRIEVAL))
            k_search = min(200, len(chunk_ids))
            distances, indices = index.search(query_embedding, k_search)

            retrieved_chunks: List[Dict[str, Any]] = []
            for idx, dist in zip(indices[0], distances[0]):
                if idx == -1:
                    continue
                similarity = 1.0 - float(dist)
                if similarity < settings.SIMILARITY_THRESHOLD:
                    continue
                chunk_id = chunk_ids[int(idx)]
                chunk = db.query(Chunk).filter(Chunk.chunk_id == chunk_id).first()
                if not chunk:
                    continue
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

            retrieval_candidates_gauge.labels(book_id=book_id).set(len(retrieved_chunks))

            if not retrieved_chunks:
                resp = dict(FALLBACK_RESPONSE)
                self.cache.set(book_id, qhash, resp)
                return resp

            # Diversity: prefer diverse chapters (simple pass)
            retrieved_chunks = self._dedupe_by_chapter(retrieved_chunks, limit=max(top_k * 3, top_k))

            # Rerank
            if settings.RERANK_ENABLED and len(retrieved_chunks) > top_k:
                t0 = time.time()
                retrieved_chunks = await self._rerank(question, retrieved_chunks)
                rerank_latency_seconds.labels(book_id=book_id).observe(time.time() - t0)

            final_chunks = retrieved_chunks[:top_k]

            # PII redaction for generator input
            redacted_chunks, pii_redacted = self._redact_pii_from_chunks(final_chunks)

            # Generate
            t_gen = time.time()
            response = await self._generate_answer(
                book_id=book_id,
                question=question,
                chunks=redacted_chunks,
                book_profile=book.book_profile,
                history=history,
                options=options,
            )
            generation_latency_seconds.labels(book_id=book_id).observe(time.time() - t_gen)

            # Confidence: conservative mapping from max similarity
            max_sim = max((c.get("similarity", 0.0) for c in final_chunks), default=0.0)
            response["confidence"] = float(self._compute_confidence(max_sim))

            # Notes
            if pii_redacted:
                response["notes"] = "redacted_pii"

            # Normalize sources: subset of retrieved
            retrieved_ids = [c["chunk_id"] for c in final_chunks]
            retrieved_set = set(retrieved_ids)
            sources = response.get("sources") if isinstance(response.get("sources"), list) else []
            sources = [s for s in sources if isinstance(s, str) and s in retrieved_set]
            if not sources:
                sources = retrieved_ids[:2]
            response["sources"] = sources

            # Validator gate
            vr = self.validator.validate(response, retrieved_chunks=final_chunks, min_confidence=0.35)
            if not vr.ok:
                resp = dict(FALLBACK_RESPONSE)
                resp["notes"] = vr.notes or "validator_rejected"
                self.cache.set(book_id, qhash, resp)
                return resp

            # Strict low-confidence fallback
            if float(response.get("confidence", 0.0)) < 0.35:
                resp = dict(FALLBACK_RESPONSE)
                resp["notes"] = "unsure"
                self.cache.set(book_id, qhash, resp)
                return resp

            self.cache.set(book_id, qhash, response)
            return response

        finally:
            db.close()

    async def _rerank(self, question: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rerank chunks using cross-encoder (lazy-loaded)."""
        try:
            if self._rerank_model is None:
                from sentence_transformers import CrossEncoder

                self._rerank_model = CrossEncoder(settings.RERANK_MODEL)
            model = self._rerank_model

            pairs = [[question, chunk["chunk_text"]] for chunk in chunks]
            scores = model.predict(pairs)
            chunk_scores = list(zip(chunks, scores))
            chunk_scores.sort(key=lambda x: float(x[1]), reverse=True)
            return [chunk for chunk, _score in chunk_scores]
        except Exception:
            # Fail-open: keep original ranking to preserve availability
            return chunks

    async def _generate_answer(
        self,
        book_id: str,
        question: str,
        chunks: List[Dict[str, Any]],
        book_profile: Dict[str, Any],
        history: List[Dict[str, str]],
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate answer using LLM (JSON mode) with strict runtime prompt."""
        system_prompt = self._runtime_prompt

        chunks_text = "\n\n".join(
            [
                f"--- Chunk {i+1} (ID: {ch['chunk_id']}, Similarity: {ch['similarity']:.3f}) ---\n{ch['chunk_text']}"
                for i, ch in enumerate(chunks)
            ]
        )

        history_text = ""
        for turn in (history[-5:] if history else []):
            history_text += f"User: {turn.get('user', '')}\n"
            history_text += f"Assistant: {turn.get('assistant', '')}\n\n"

        user_prompt = f"""BOOK_ID: {book_id}
BOOK_PROFILE: {json.dumps(book_profile.get("book_profile", {}), indent=2)}

RETRIEVED_CHUNKS:
{chunks_text}

CONVERSATION_HISTORY:
{history_text}

USER_QUESTION: {question}"""

        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=settings.DEFAULT_LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=float(options.get("temperature", 0.2)),
            response_format={"type": "json_object"},
        )

        raw = resp.choices[0].message.content
        try:
            result = json.loads(raw)
        except Exception:
            return dict(FALLBACK_RESPONSE)

        # Ensure required keys exist
        out = {
            "answer": result.get("answer", FALLBACK_RESPONSE["answer"]),
            "confidence": float(result.get("confidence", 0.0)),
            "style_score": result.get("style_score", "summary"),
            "sources": result.get("sources", []),
            "explanation": result.get("explanation", FALLBACK_RESPONSE["explanation"]),
            "notes": result.get("notes"),
        }
        return out

    def _load_runtime_prompt(self) -> str:
        p = Path(__file__).resolve().parents[1] / "core" / "system_prompt_runtime.txt"
        if p.exists():
            return p.read_text(encoding="utf-8")
        alt = Path("backend/app/core/system_prompt_runtime.txt")
        if alt.exists():
            return alt.read_text(encoding="utf-8")
        return "You are Talk to the Book. Output JSON only."

    def _compute_confidence(self, max_similarity: float) -> float:
        x = float(max_similarity)
        if x < 0.0:
            x = 0.0
        if x > 1.0:
            x = 1.0
        return max(0.0, min(1.0, 0.95 * x))

    def _dedupe_by_chapter(self, chunks: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        seen = set()
        out = []
        for ch in chunks:
            chap = ch.get("chapter")
            key = chap if chap is not None else ("none", ch.get("chunk_id"))
            if key in seen:
                continue
            seen.add(key)
            out.append(ch)
            if len(out) >= limit:
                break
        return out

    def _redact_pii_from_chunks(self, chunks: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
        email_re = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
        phone_re = re.compile(r"\b(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{2,4}\)?[\s\-]?)?\d{3}[\s\-]?\d{4}\b")
        ssn_re = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

        redacted_any = False
        out: List[Dict[str, Any]] = []
        for ch in chunks:
            txt = str(ch.get("chunk_text", ""))
            new_txt = email_re.sub("[REDACTED_EMAIL]", txt)
            new_txt = phone_re.sub("[REDACTED_PHONE]", new_txt)
            new_txt = ssn_re.sub("[REDACTED_SSN]", new_txt)
            if new_txt != txt:
                redacted_any = True
            new_ch = dict(ch)
            new_ch["chunk_text"] = new_txt
            out.append(new_ch)
        return out, redacted_any
