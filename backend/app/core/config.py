"""
Application configuration.
"""

import os
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )

    # App
    APP_NAME: str = "Talk to the Book"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    VERSION: str = "1.0.0"

    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./talk_to_the_book.db")

    # Storage
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "local")  # local or s3
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./storage")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")

    # Encryption
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "change-me-in-production")

    # LLM APIs
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")

    # Embeddings
    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2"
    )
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))

    # Vector DB
    VECTOR_DB_TYPE: str = os.getenv(
        "VECTOR_DB_TYPE", "faiss"
    )  # faiss, qdrant, weaviate
    FAISS_INDEX_PATH: str = os.getenv("FAISS_INDEX_PATH", "./storage/indices")
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")

    # Retrieval
    TOP_K_RETRIEVAL: int = int(os.getenv("TOP_K_RETRIEVAL", "6"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.12"))
    RERANK_ENABLED: bool = os.getenv("RERANK_ENABLED", "true").lower() == "true"
    RERANK_MODEL: str = os.getenv(
        "RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    RERANK_K: int = int(os.getenv("RERANK_K", "50"))
    FINAL_K: int = int(os.getenv("FINAL_K", "6"))

    MAX_UPLOAD_BYTES: int = 100 * 1024 * 1024
    LLM_TIMEOUT_SECONDS: float = 60.0

    # Chunking defaults
    DEFAULT_CHUNK_SIZE: int = int(os.getenv("DEFAULT_CHUNK_SIZE", "600"))
    DEFAULT_OVERLAP_PERCENT: int = int(os.getenv("DEFAULT_OVERLAP_PERCENT", "20"))

    # Monitoring
    PROMETHEUS_ENABLED: bool = os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true"
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")

    # Security
    RETENTION_DAYS: int = int(os.getenv("RETENTION_DAYS", "180"))
    REQUIRE_USER_CONSENT: bool = (
        os.getenv("REQUIRE_USER_CONSENT", "true").lower() == "true"
    )


settings = Settings()
