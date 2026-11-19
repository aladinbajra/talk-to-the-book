"""
Query endpoint for asking questions about books.
"""

import time
import uuid
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.metrics import (
    average_confidence_gauge,
    generation_latency_seconds,
    query_count_total,
    query_latency_seconds,
    retrieval_latency_seconds,
    unknown_rate_counter,
)
from app.db.database import get_db
from app.db.models import Book, Query
from app.services.query import QueryService

router = APIRouter()


class QueryOptions(BaseModel):
    top_k: int = Field(default=6, ge=1, le=20)
    style: Literal["concise", "detailed", "voice"] = "concise"


class ConversationTurn(BaseModel):
    user: str = Field(default="", max_length=4000)
    assistant: str = Field(default="", max_length=12000)


class QueryRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    book_id: str
    user_id: Optional[str] = None
    question: str = Field(min_length=1, max_length=4000)
    history: Optional[List[ConversationTurn]] = Field(default=None, max_length=10)
    options: Optional[QueryOptions] = None


class QueryResponse(BaseModel):
    answer: str
    confidence: float
    style_score: str
    sources: List[str]
    source_details: List[Dict[str, Any]] = Field(default_factory=list)
    explanation: str
    notes: Optional[str] = None


@router.post("/query", response_model=QueryResponse)
async def query_book(request: QueryRequest, db: Session = Depends(get_db)):
    """
    Query a book and get an answer.
    """
    start_time = time.time()

    # Get book
    book = db.query(Book).filter(Book.book_id == request.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.ingest_status != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"Book not ready. Current status: {book.ingest_status}",
        )

    # Process query
    query_service = QueryService()

    try:
        # Retrieve and generate
        retrieval_start = time.time()
        response = await query_service.process_query(
            book_id=request.book_id,
            question=request.question,
            history=[turn.model_dump() for turn in request.history or []],
            options=request.options.model_dump() if request.options else {},
        )
        retrieval_time = time.time() - retrieval_start

        # Record metrics
        total_time = time.time() - start_time
        query_latency_seconds.labels(book_id=request.book_id).observe(total_time)
        retrieval_latency_seconds.labels(book_id=request.book_id).observe(
            retrieval_time
        )
        query_count_total.labels(book_id=request.book_id, status="success").inc()

        if response.get("notes") == "UNKNOWN IN BOOK":
            unknown_rate_counter.labels(book_id=request.book_id).inc()

        if response.get("confidence"):
            average_confidence_gauge.labels(book_id=request.book_id).set(
                response["confidence"]
            )

        # Save query to database
        query_id = str(uuid.uuid4())
        query_record = Query(
            query_id=query_id,
            book_id=request.book_id,
            user_id=request.user_id,
            question=request.question,
            response=response,
            confidence=response.get("confidence", 0.0),
            answer_type=response.get("style_score", "factual"),
            source_chunk_ids=response.get("sources", []),
        )
        db.add(query_record)
        db.commit()

        return response

    except Exception as e:
        query_count_total.labels(book_id=request.book_id, status="error").inc()
        import logging

        db.rollback()
        logging.getLogger(__name__).exception("Book query failed")
        raise HTTPException(
            status_code=503,
            detail="The answer service is unavailable. Please retry shortly.",
        ) from e
