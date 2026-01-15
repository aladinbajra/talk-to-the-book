"""
Ingest endpoints for processing books.
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Book
from app.services.ingest import IngestService
from app.core.config import settings

router = APIRouter()


class IngestStartRequest(BaseModel):
    book_id: str
    options: Optional[Dict[str, Any]] = None


class IngestStatusResponse(BaseModel):
    book_id: str
    status: str
    progress: Optional[float] = None
    issues: Optional[list] = None


@router.post("/ingest/start")
async def start_ingest(
    request: IngestStartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start ingest process for a book.
    """
    # Get book
    book = db.query(Book).filter(Book.book_id == request.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if book.ingest_status == "ready":
        return {
            "book_id": request.book_id,
            "status": "already_ready",
            "message": "Book is already ingested and ready"
        }
    
    if book.ingest_status in ["parsing", "chunking", "embedding"]:
        return {
            "book_id": request.book_id,
            "status": "in_progress",
            "message": "Ingest already in progress"
        }
    
    # Update status
    book.ingest_status = "parsing"
    db.commit()
    
    # Start background ingest
    ingest_service = IngestService()
    background_tasks.add_task(
        ingest_service.process_book,
        book_id=request.book_id,
        options=request.options or {}
    )
    
    return {
        "ingest_job_id": request.book_id,
        "book_id": request.book_id,
        "status": "started",
        "message": "Ingest process started"
    }


@router.get("/ingest/status")
async def get_ingest_status(
    book_id: str,
    db: Session = Depends(get_db)
):
    """
    Get ingest status for a book.
    """
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Calculate progress based on status
    progress_map = {
        "uploaded": 0.0,
        "parsing": 0.2,
        "chunking": 0.4,
        "embedding": 0.7,
        "ready": 1.0,
        "error": 0.0
    }
    
    progress = progress_map.get(book.ingest_status, 0.0)
    
    return {
        "book_id": book_id,
        "status": book.ingest_status,
        "progress": progress,
        "issues": []  # Could be populated from error logs
    }
