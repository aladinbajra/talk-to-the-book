"""
Database models.
"""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class Book(Base):
    """Book model."""

    __tablename__ = "books"

    book_id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=True)
    author = Column(String, nullable=True)
    language = Column(String, default="en")
    file_path = Column(String, nullable=False)
    file_format = Column(String)  # pdf, txt, epub
    ingest_status = Column(
        String, default="uploaded"
    )  # uploaded, parsing, chunking, embedding, ready, error
    total_words = Column(Integer, nullable=True)
    total_pages_estimate = Column(Integer, nullable=True)
    copyright_flag = Column(
        String, default="unknown"
    )  # public_domain, clearly_copyrighted, unknown
    book_profile = Column(JSON, nullable=True)  # Full book profile JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    chunks = relationship("Chunk", back_populates="book", cascade="all, delete-orphan")
    queries = relationship("Query", back_populates="book", cascade="all, delete-orphan")


class Chunk(Base):
    """Chunk model."""

    __tablename__ = "chunks"

    chunk_id = Column(String, primary_key=True, index=True)
    book_id = Column(String, ForeignKey("books.book_id"), nullable=False, index=True)
    start_loc = Column(String)
    end_loc = Column(String)
    chapter_number = Column(Integer, default=0)
    excerpt_hint = Column(String)
    token_estimate = Column(Integer)
    chunk_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    book = relationship("Book", back_populates="chunks")


class Query(Base):
    """Query model."""

    __tablename__ = "queries"

    query_id = Column(String, primary_key=True, index=True)
    book_id = Column(String, ForeignKey("books.book_id"), nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)
    question = Column(Text, nullable=False)
    response = Column(JSON, nullable=False)  # Full response JSON
    confidence = Column(Float)
    answer_type = Column(String)  # factual, interpretive, summary, unknown
    source_chunk_ids = Column(JSON)  # List of chunk IDs
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    book = relationship("Book", back_populates="queries")
    feedback = relationship(
        "Feedback", back_populates="query", uselist=False, cascade="all, delete-orphan"
    )


class Feedback(Base):
    """User feedback model."""

    __tablename__ = "feedback"

    feedback_id = Column(String, primary_key=True, index=True)
    query_id = Column(
        String, ForeignKey("queries.query_id"), nullable=False, unique=True, index=True
    )
    user_feedback = Column(String)  # up, down
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    query = relationship("Query", back_populates="feedback")
