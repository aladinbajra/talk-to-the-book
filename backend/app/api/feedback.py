"""
Feedback endpoint for user ratings.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.metrics import feedback_positive_rate_gauge
from app.db.database import get_db
from app.db.models import Feedback, Query

router = APIRouter()


class FeedbackRequest(BaseModel):
    query_id: str
    feedback: str  # "up" or "down"
    comment: Optional[str] = None


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """
    Submit feedback for a query.
    """
    if request.feedback not in ["up", "down"]:
        raise HTTPException(status_code=400, detail="Feedback must be 'up' or 'down'")

    # Get query
    query = db.query(Query).filter(Query.query_id == request.query_id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")

    # Check if feedback already exists
    existing = db.query(Feedback).filter(Feedback.query_id == request.query_id).first()
    if existing:
        # Update existing
        existing.user_feedback = request.feedback
        existing.comment = request.comment
    else:
        # Create new
        feedback = Feedback(
            feedback_id=str(uuid.uuid4()),
            query_id=request.query_id,
            user_feedback=request.feedback,
            comment=request.comment,
        )
        db.add(feedback)

    db.commit()

    # Update metrics
    # Calculate positive rate for this book
    total_feedback = (
        db.query(func.count(Feedback.feedback_id))
        .filter(
            Feedback.query_id.in_(
                db.query(Query.query_id).filter(Query.book_id == query.book_id)
            )
        )
        .scalar()
        or 0
    )

    positive_feedback = (
        db.query(func.count(Feedback.feedback_id))
        .filter(
            Feedback.query_id.in_(
                db.query(Query.query_id).filter(Query.book_id == query.book_id)
            ),
            Feedback.user_feedback == "up",
        )
        .scalar()
        or 0
    )

    if total_feedback > 0:
        positive_rate = positive_feedback / total_feedback
        feedback_positive_rate_gauge.labels(book_id=query.book_id).set(positive_rate)

    return {"success": True, "message": "Feedback recorded"}
