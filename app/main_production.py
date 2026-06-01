"""Production-ready main.py with database and cache initialization."""

import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.database.cache import init_cache, close_cache, check_cache_health
from app.database.connection import init_db, close_db, check_db_health

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


# ============================================================================
# Request/Response Middleware
# ============================================================================

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to all requests."""
    
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests and responses."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        process_time = time.time() - start_time
        
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Duration: {process_time * 1000:.2f}ms - "
            f"Request-ID: {request.state.request_id}"
        )
        
        response.headers["X-Process-Time"] = str(process_time)
        return response


class ResponseEnvelopeMiddleware(BaseHTTPMiddleware):
    """Wrap all responses in standard envelope."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Don't wrap non-JSON responses (health checks, static files, etc)
        if not request.url.path.startswith(settings.API_PREFIX):
            return response
        
        # For error responses, return as-is
        if response.status_code >= 400:
            return response
        
        return response  # Already handled by routers with status_code


# ============================================================================
# Health Checks
# ============================================================================

async def startup_checks():
    """Run startup health checks."""
    logger.info("Running startup checks...")
    
    # Check database
    db_health = await check_db_health()
    if not db_health:
        logger.error("Database health check failed!")
        return False
    logger.info("✓ Database healthy")
    
    # Check cache
    cache_health = await check_cache_health()
    if not cache_health:
        logger.warning("Cache health check failed - using fallback")
    else:
        logger.info("✓ Cache healthy")
    
    return True


# ============================================================================
# Lifespan Events
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    
    # Startup
    logger.info("Starting Smart Interview Intelligence API")
    logger.info(f"Environment: DEBUG={settings.DEBUG}, LOG_LEVEL={settings.LOG_LEVEL}")
    
    # Initialize database
    await init_db()
    logger.info("Database connection pool initialized")
    
    # Initialize cache
    await init_cache()
    logger.info("Cache connection initialized")
    
    # Run startup checks
    if not await startup_checks():
        logger.error("Startup checks failed!")
        raise RuntimeError("Startup checks failed")
    
    logger.info("✓ Application startup complete")
    
    yield  # Application running
    
    # Shutdown
    logger.info("Shutting down application...")
    await close_db()
    await close_cache()
    logger.info("✓ Application shutdown complete")


# ============================================================================
# Application Factory
# ============================================================================

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Scalable AI-powered interview intelligence platform",
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    # ========================================================================
    # CORS Configuration
    # ========================================================================
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # ========================================================================
    # Middleware Stack (order matters)
    # ========================================================================
    
    # 1. Request ID (outermost)
    app.add_middleware(RequestIDMiddleware)
    
    # 2. Logging
    app.add_middleware(LoggingMiddleware)
    
    # 3. Response Envelope
    app.add_middleware(ResponseEnvelopeMiddleware)
    
    # ========================================================================
    # Exception Handlers
    # ========================================================================
    
    register_exception_handlers(app)
    
    # ========================================================================
    # Routes
    # ========================================================================
    
    # Include all API routes
    app.include_router(router, prefix=settings.API_PREFIX)
    
    # ========================================================================
    # Health Check Endpoints
    # ========================================================================
    
    @app.get("/health", tags=["system"])
    async def health_check():
        """Simple health check (used by load balancers)."""
        return {"status": "ok", "version": settings.VERSION}
    
    @app.get("/ready", tags=["system"])
    async def readiness_check():
        """Readiness check (used by Kubernetes)."""
        db_ok = await check_db_health()
        cache_ok = await check_cache_health()
        
        if not db_ok:
            return JSONResponse(
                {"status": "not_ready", "reason": "database"},
                status_code=503
            )
        
        return {"status": "ready", "version": settings.VERSION}
    
    @app.get("/metrics/health", tags=["system"])
    async def detailed_health():
        """Detailed health metrics (for monitoring)."""
        return {
            "status": "ok",
            "database": {"connected": await check_db_health()},
            "cache": {"connected": await check_cache_health()},
            "version": settings.VERSION,
            "timestamp": time.time(),
        }
    
    # ========================================================================
    # Info Endpoints
    # ========================================================================
    
    @app.get("/info", tags=["system"])
    async def app_info():
        """Application information."""
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "debug": settings.DEBUG,
            "api_prefix": settings.API_PREFIX,
        }
    
    logger.info("✓ FastAPI application created")
    
    return app


# ============================================================================
# Application Instance
# ============================================================================

app = create_app()

# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting Uvicorn server on 0.0.0.0:8000")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )
