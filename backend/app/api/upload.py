"""
Upload endpoint for book files.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uuid
import os
from pathlib import Path
import hashlib
from datetime import datetime

from app.db.database import get_db
from app.db.models import Book
from app.core.config import settings
from app.services.storage import StorageService
from app.services.encryption import EncryptionService

router = APIRouter()


@router.post("/upload")
async def upload_book(
    file: UploadFile = File(...),
    user_consent: bool = False,
    db: Session = Depends(get_db)
):
    """
    Upload a book file (PDF, TXT, or ePub).
    
    Returns book_id and status.
    """
    # Validate file type
    allowed_extensions = {".pdf", ".txt", ".epub"}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Check user consent if required
    if settings.REQUIRE_USER_CONSENT and not user_consent:
        raise HTTPException(
            status_code=400,
            detail="User consent required. Please confirm you have the right to upload this book."
        )
    
    # Generate book_id
    book_id = str(uuid.uuid4())
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Validate file size (max 100MB)
    max_size = 100 * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {max_size / (1024*1024)}MB"
        )
    
    # Store file
    storage_service = StorageService()
    file_path = await storage_service.store_file(
        book_id=book_id,
        filename=file.filename,
        content=content,
        file_format=file_ext[1:]  # Remove dot
    )
    
    # Encrypt file if configured
    if settings.ENCRYPTION_KEY != "change-me-in-production":
        encryption_service = EncryptionService()
        encrypted_path = await encryption_service.encrypt_file(file_path)
        file_path = encrypted_path
    
    # Create book record
    book = Book(
        book_id=book_id,
        title=file.filename,
        file_path=file_path,
        file_format=file_ext[1:],
        ingest_status="uploaded",
        copyright_flag="unknown"
    )
    
    db.add(book)
    db.commit()
    db.refresh(book)
    
    return {
        "book_id": book_id,
        "status": "uploaded",
        "filename": file.filename,
        "file_size": file_size,
        "message": "File uploaded successfully. Start ingest with /ingest/start"
    }
