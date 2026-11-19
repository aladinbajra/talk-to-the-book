"""
Upload endpoint for book files.
"""

import hashlib
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import Book
from app.services.encryption import EncryptionService
from app.services.storage import StorageService

router = APIRouter()


@router.post("/upload")
async def upload_book(
    file: UploadFile = File(...),
    user_consent: bool = Form(False),
    db: Session = Depends(get_db),
):
    """
    Upload a book file (PDF, TXT, or ePub).

    Returns book_id and status.
    """
    # Validate file type
    allowed_extensions = {".pdf", ".txt", ".epub"}
    filename = Path((file.filename or "").replace("\\", "/")).name
    file_ext = Path(filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}",
        )

    # Check user consent if required
    if settings.REQUIRE_USER_CONSENT and not user_consent:
        raise HTTPException(
            status_code=400,
            detail="User consent required. Please confirm you have the right to upload this book.",
        )

    # Generate book_id
    book_id = str(uuid.uuid4())

    # Read at most the configured limit, never an unbounded request body.
    content = bytearray()
    try:
        while True:
            part = await file.read(
                min(1024 * 1024, settings.MAX_UPLOAD_BYTES + 1 - len(content))
            )
            if not part:
                break
            content.extend(part)
            if len(content) > settings.MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413, detail="File exceeds the upload size limit."
                )
    finally:
        await file.close()
    file_size = len(content)
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if file_ext == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="This file is not a PDF.")
    if file_ext == ".epub" and not content.startswith(b"PK"):
        raise HTTPException(status_code=400, detail="This file is not an ePub archive.")
    stored_content = bytes(content)
    stored_format = file_ext[1:]
    if settings.ENCRYPTION_KEY != "change-me-in-production":
        stored_content = EncryptionService().encrypt_bytes(stored_content)
        stored_format += ".encrypted"
    storage_service = StorageService()
    file_path = await storage_service.store_file(
        book_id, filename, stored_content, stored_format
    )

    # Create book record
    book = Book(
        book_id=book_id,
        title=filename,
        file_path=file_path,
        file_format=file_ext[1:],
        ingest_status="uploaded",
        copyright_flag="unknown",
    )

    db.add(book)
    db.commit()
    db.refresh(book)

    return {
        "book_id": book_id,
        "status": "uploaded",
        "filename": filename,
        "file_size": file_size,
        "message": "File uploaded successfully. Start ingest with /ingest/start",
    }
