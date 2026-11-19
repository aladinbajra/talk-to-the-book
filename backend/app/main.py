"""
FastAPI main application for Talk to the Book.
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import books, delete, feedback, ingest, query, upload
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.metrics import metrics_router
from app.db.database import init_db

# Setup logging
setup_logging()

# Metrics
from prometheus_client import Counter, Gauge, Histogram

from app.core.metrics import (
    average_confidence_gauge,
    feedback_positive_rate_gauge,
    query_count_total,
    query_latency_seconds,
    unknown_rate_counter,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    print("Initializing database...")
    await init_db()
    print("Database initialized.")
    yield
    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="Talk to the Book API",
    description="Production-ready API for interactive book Q&A",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Error handling
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred",
        },
    )


# Include routers
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(ingest.router, prefix="/api/v1", tags=["ingest"])
app.include_router(query.router, prefix="/api/v1", tags=["query"])
app.include_router(books.router, prefix="/api/v1", tags=["books"])
app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])
app.include_router(delete.router, prefix="/api/v1", tags=["delete"])
app.include_router(metrics_router, prefix="/metrics", tags=["metrics"])


@app.get("/")
async def root():
    return {
        "service": "Talk to the Book API",
        "version": "1.0.0",
        "status": "healthy",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "talk-to-the-book"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
