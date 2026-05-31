"""FastAPI application entry point."""

import json
import logging
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers


settings = get_settings()
REQUEST_COUNT = 0
REQUEST_LATENCY_SECONDS: list[float] = []
RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
logger = logging.getLogger("smart_interview")
logging.basicConfig(level=logging.INFO, format="%(message)s")

app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description="AI-assisted resume screening, ranking, skill gap analysis, and interview question generation.",
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect request count and latency for Prometheus fallback metrics."""

    async def dispatch(self, request, call_next):
        global REQUEST_COUNT
        start = time.perf_counter()
        request_id = request.headers.get("x-request-id", str(uuid4()))
        response = await call_next(request)
        REQUEST_COUNT += 1
        elapsed = time.perf_counter() - start
        REQUEST_LATENCY_SECONDS.append(elapsed)
        response.headers["x-request-id"] = request_id
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "latency_ms": round(elapsed * 1000, 2),
                }
            )
        )
        return response


class GuardrailMiddleware(BaseHTTPMiddleware):
    """Apply optional API key auth and a lightweight per-client rate limit."""

    async def dispatch(self, request, call_next):
        path = request.url.path
        if settings.api_key and path.startswith(settings.api_prefix):
            supplied_key = request.headers.get("x-api-key")
            if supplied_key != settings.api_key:
                return JSONResponse(status_code=401, content={"detail": "Valid X-API-Key header required."})

        client = request.client.host if request.client else "unknown"
        now = time.time()
        bucket = RATE_BUCKETS[client]
        while bucket and bucket[0] <= now - 60:
            bucket.popleft()
        if len(bucket) >= settings.rate_limit_per_minute:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again shortly."})
        bucket.append(now)
        return await call_next(request)


app.add_middleware(GuardrailMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(router, prefix=settings.api_prefix)

try:
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(app)
except Exception:
    pass


@app.get("/", tags=["health"])
def root() -> dict[str, str]:
    """Return basic service metadata."""
    return {
        "service": settings.project_name,
        "version": settings.version,
        "status": "ok",
    }


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Health check endpoint for load balancers and uptime probes."""
    return {"status": "healthy"}


@app.get("/metrics", response_class=PlainTextResponse, tags=["monitoring"])
def metrics() -> str:
    """Prometheus-compatible fallback metrics."""
    total_latency = sum(REQUEST_LATENCY_SECONDS)
    avg_latency = total_latency / len(REQUEST_LATENCY_SECONDS) if REQUEST_LATENCY_SECONDS else 0.0
    return "\n".join(
        [
            "# HELP request_count Total HTTP requests handled.",
            "# TYPE request_count counter",
            f"request_count {REQUEST_COUNT}",
            "# HELP latency Average request latency in seconds.",
            "# TYPE latency gauge",
            f"latency {avg_latency:.6f}",
            "# HELP prediction_time Candidate prediction timer placeholder.",
            "# TYPE prediction_time gauge",
            "prediction_time 0",
        ]
    )
