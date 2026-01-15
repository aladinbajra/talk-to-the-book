"""
Prometheus metrics for monitoring.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import APIRouter, Response

# Metrics
query_count_total = Counter(
    "query_count_total",
    "Total number of queries",
    ["book_id", "status"]
)

query_latency_seconds = Histogram(
    "query_latency_seconds",
    "Query latency in seconds",
    ["book_id"],
    buckets=[0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
)

unknown_rate_counter = Counter(
    "unknown_responses_total",
    "Total number of UNKNOWN IN BOOK responses",
    ["book_id"]
)

average_confidence_gauge = Gauge(
    "average_confidence",
    "Average confidence score",
    ["book_id"]
)

feedback_positive_rate_gauge = Gauge(
    "feedback_positive_rate",
    "Positive feedback rate",
    ["book_id"]
)

ingest_duration_seconds = Histogram(
    "ingest_duration_seconds",
    "Ingest duration in seconds",
    ["book_id", "status"]
)

retrieval_latency_seconds = Histogram(
    "retrieval_latency_seconds",
    "Retrieval latency in seconds",
    ["book_id"]
)

generation_latency_seconds = Histogram(
    "generation_latency_seconds",
    "Generation latency in seconds",
    ["book_id"]
)

# Router for metrics endpoint
metrics_router = APIRouter()


@metrics_router.get("")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
