"""
Delete book endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Book
from app.services.storage import StorageService

router = APIRouter()


class DeleteBookRequest(BaseModel):
    book_id: str


@router.post("/delete_book")
async def delete_book(request: DeleteBookRequest, db: Session = Depends(get_db)):
    """
    Permanently delete a book and all associated data.
    """
    book = db.query(Book).filter(Book.book_id == request.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.ingest_status in {"parsing", "chunking", "embedding"}:
        raise HTTPException(
            status_code=409,
            detail="Wait for processing to finish before deleting this book.",
        )

    # Delete from storage
    storage_service = StorageService()
    await storage_service.delete_book(request.book_id)

    # Delete from database (cascade will handle related records)
    db.delete(book)
    db.commit()

    return {"success": True, "message": f"Book {request.book_id} deleted successfully"}
