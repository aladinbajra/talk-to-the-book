"""
Books listing endpoint.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.db.models import Book, Query

router = APIRouter()


@router.get("/books")
async def list_books(db: Session = Depends(get_db)):
    """
    List all books with metadata.
    """
    books = db.query(Book).all()
    
    result = []
    for book in books:
        # Get query count
        query_count = db.query(func.count(Query.query_id)).filter(
            Query.book_id == book.book_id
        ).scalar() or 0
        
        # Get last used time
        last_query = db.query(Query).filter(
            Query.book_id == book.book_id
        ).order_by(Query.created_at.desc()).first()
        
        result.append({
            "book_id": book.book_id,
            "title": book.title,
            "author": book.author,
            "language": book.language,
            "file_format": book.file_format,
            "ingest_status": book.ingest_status,
            "total_words": book.total_words,
            "total_pages_estimate": book.total_pages_estimate,
            "copyright_flag": book.copyright_flag,
            "created_at": book.created_at.isoformat() if book.created_at else None,
            "updated_at": book.updated_at.isoformat() if book.updated_at else None,
            "question_count": query_count,
            "last_used": last_query.created_at.isoformat() if last_query else None,
        })
    
    return {"books": result}
