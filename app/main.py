"""FastAPI application entry point."""

import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers


settings = get_settings()
REQUEST_COUNT = 0
REQUEST_LATENCY_SECONDS: list[float] = []

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
        response = await call_next(request)
        REQUEST_COUNT += 1
        REQUEST_LATENCY_SECONDS.append(time.perf_counter() - start)
        return response


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
