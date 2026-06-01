"""FIXED: Thread-safe middleware for metrics and rate limiting.

Replaces the unsafe global collections in main.py with thread-safe versions.
"""

import json
import logging
import threading
import time
from collections import defaultdict, deque
from uuid import uuid4
from typing import Optional

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse


logger = logging.getLogger("smart_interview")


class ThreadSafeMetricsCollector:
    """🔧 Thread-safe metrics collection with locks."""
    
    def __init__(self):
        self.request_count = 0
        self.request_latencies: deque[float] = deque(maxlen=1000)
        self._lock = threading.RLock()
    
    def record_request(self, latency: float) -> None:
        """Record a request latency (thread-safe)."""
        with self._lock:
            self.request_count += 1
            self.request_latencies.append(latency)
    
    def get_stats(self) -> dict[str, float]:
        """Get current metrics (thread-safe)."""
        with self._lock:
            if not self.request_latencies:
                return {"count": self.request_count, "avg_latency_ms": 0.0}
            avg = sum(self.request_latencies) / len(self.request_latencies)
            return {
                "count": self.request_count,
                "avg_latency_ms": round(avg * 1000, 2),
                "max_latency_ms": round(max(self.request_latencies) * 1000, 2),
            }


class ThreadSafeRateLimiter:
    """🔧 Thread-safe rate limiter for per-client limits."""
    
    def __init__(self, limit_per_minute: int = 120):
        self.limit_per_minute = limit_per_minute
        self.buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.RLock()
    
    def is_allowed(self, client_id: str, window_seconds: int = 60) -> bool:
        """Check if client is within rate limit (thread-safe)."""
        now = time.time()
        
        with self._lock:
            bucket = self.buckets[client_id]
            
            # Remove old entries outside window
            while bucket and bucket[0] <= now - window_seconds:
                bucket.popleft()
            
            # Check limit
            if len(bucket) >= self.limit_per_minute:
                return False
            
            # Record this request
            bucket.append(now)
            return True


# Global thread-safe instances
metrics_collector = ThreadSafeMetricsCollector()
rate_limiter = ThreadSafeRateLimiter(limit_per_minute=120)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect request metrics safely for Prometheus fallback."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        request_id = request.headers.get("x-request-id", str(uuid4()))
        
        try:
            response = await call_next(request)
        except Exception as exc:
            # Still log failed requests
            elapsed = time.perf_counter() - start
            metrics_collector.record_request(elapsed)
            logger.error(
                json.dumps({
                    "event": "http_request",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "latency_ms": round(elapsed * 1000, 2),
                    "error": str(exc),
                })
            )
            raise
        
        # Record successful request
        elapsed = time.perf_counter() - start
        metrics_collector.record_request(elapsed)
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
    """🔧 FIXED: Thread-safe API key and rate limiting."""

    def __init__(self, app, settings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # API key check
        if self.settings.api_key and path.startswith(self.settings.api_prefix):
            supplied_key = request.headers.get("x-api-key")
            if supplied_key != self.settings.api_key:
                return JSONResponse(
                    status_code=401, 
                    content={"detail": "Valid X-API-Key header required."}
                )
        
        # Rate limiting (thread-safe)
        client_id = request.client.host if request.client else "unknown"
        if not rate_limiter.is_allowed(client_id):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded (120 per minute). Try again shortly."}
            )
        
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Set browser security headers for the vanilla dashboard."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


def setup_middleware(app: FastAPI, settings) -> None:
    """🔧 Consolidated middleware setup with correct ordering."""
    # Order matters: security first, then metrics, then app logic
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(GuardrailMiddleware, settings=settings)
