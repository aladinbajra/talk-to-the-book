"""
Ingest endpoints for processing books.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import Book
from app.services.ingest import IngestService

router = APIRouter()


class IngestOptions(BaseModel):
    chunk_size: int = Field(default=600, ge=20, le=3000)
    overlap_percent: int = Field(default=20, ge=0, le=50)


class IngestStartRequest(BaseModel):
    book_id: str
    options: Optional[IngestOptions] = None


class IngestStatusResponse(BaseModel):
    book_id: str
    status: str
    progress: Optional[float] = None
    issues: Optional[list] = None


@router.post("/ingest/start")
async def start_ingest(
    request: IngestStartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
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
            "message": "Book is already ingested and ready",
        }

    if book.ingest_status in ["parsing", "chunking", "embedding"]:
        return {
            "book_id": request.book_id,
            "status": "in_progress",
            "message": "Ingest already in progress",
        }

    # Update status
    started = (
        db.query(Book)
        .filter(
            Book.book_id == request.book_id,
            Book.ingest_status.in_(["uploaded", "error"]),
        )
        .update({"ingest_status": "parsing"}, synchronize_session=False)
    )
    db.commit()
    if started != 1:
        return {
            "book_id": request.book_id,
            "status": "in_progress",
            "message": "Ingest already in progress",
        }

    # Start background ingest
    ingest_service = IngestService()
    background_tasks.add_task(
        ingest_service.process_book,
        book_id=request.book_id,
        options=request.options.model_dump() if request.options else {},
    )

    return {
        "ingest_job_id": request.book_id,
        "book_id": request.book_id,
        "status": "started",
        "message": "Ingest process started",
    }


@router.get("/ingest/status")
async def get_ingest_status(book_id: str, db: Session = Depends(get_db)):
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
        "error": 0.0,
    }

    progress = progress_map.get(book.ingest_status, 0.0)

    return {
        "book_id": book_id,
        "status": book.ingest_status,
        "progress": progress,
        "issues": (
            ["Processing failed. Check the server configuration and retry."]
            if book.ingest_status == "error"
            else []
        ),
    }
