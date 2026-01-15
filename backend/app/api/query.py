"""
Query endpoint for asking questions about books.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
import uuid
import time

from app.db.database import get_db
from app.db.models import Book, Query
from app.services.query import QueryService
from app.core.metrics import (
    query_count_total,
    query_latency_seconds,
    unknown_rate_counter,
    average_confidence_gauge,
    retrieval_latency_seconds,
    generation_latency_seconds,
)

router = APIRouter()


class QueryRequest(BaseModel):
    book_id: str
    user_id: Optional[str] = None
    question: str
    history: Optional[List[Dict[str, str]]] = None
    options: Optional[Dict[str, str]] = None  # style: "concise|detailed|voice"


class QueryResponse(BaseModel):
    answer: str
    confidence: float
    style_score: str
    sources: List[str]
    explanation: str
    notes: Optional[str] = None


@router.post("/query", response_model=QueryResponse)
async def query_book(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
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
            detail=f"Book not ready. Current status: {book.ingest_status}"
        )
    
    # Process query
    query_service = QueryService()
    
    try:
        # Retrieve and generate
        retrieval_start = time.time()
        response = await query_service.process_query(
            book_id=request.book_id,
            question=request.question,
            history=request.history or [],
            options=request.options or {}
        )
        retrieval_time = time.time() - retrieval_start
        
        # Record metrics
        total_time = time.time() - start_time
        query_latency_seconds.labels(book_id=request.book_id).observe(total_time)
        retrieval_latency_seconds.labels(book_id=request.book_id).observe(retrieval_time)
        query_count_total.labels(book_id=request.book_id, status="success").inc()
        
        if response.get("notes") == "UNKNOWN IN BOOK":
            unknown_rate_counter.labels(book_id=request.book_id).inc()
        
        if response.get("confidence"):
            average_confidence_gauge.labels(book_id=request.book_id).set(response["confidence"])
        
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
            source_chunk_ids=response.get("sources", [])
        )
        db.add(query_record)
        db.commit()
        
        return response
        
    except Exception as e:
        query_count_total.labels(book_id=request.book_id, status="error").inc()
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")
