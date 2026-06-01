# Production Implementation Guide

This guide provides step-by-step instructions for implementing the minimal production version of Smart Interview Intelligence.

## Table of Contents
1. [Setup & Installation](#setup--installation)
2. [Database Migration](#database-migration)
3. [Service Layer Updates](#service-layer-updates)
4. [API Implementation](#api-implementation)
5. [Caching Strategy](#caching-strategy)
6. [Testing & Validation](#testing--validation)
7. [Deployment](#deployment)

---

## Setup & Installation

### 1. Install Dependencies

```bash
# Add production dependencies
pip install sqlalchemy asyncpg psycopg2-binary redis pydantic-settings
pip install celery[redis]  # For async tasks
pip install prometheus-client  # For monitoring
```

### 2. Environment Configuration

Create `.env.production`:

```env
# Application
DEBUG=false
LOG_LEVEL=INFO
VERSION=1.0.0

# Security
API_KEY=your-secure-api-key-here
JWT_SECRET_KEY=your-jwt-secret-key

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/smart_interview
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=10

# Cache
REDIS_URL=redis://redis-host:6379/0

# Features
RATE_LIMIT_PER_SEC=10000
PAGE_SIZE_DEFAULT=20
PAGE_SIZE_MAX=100
```

### 3. Initialize PostgreSQL

```bash
# Using Docker
docker run -d \
  --name smart-interview-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=smart_interview \
  -p 5432:5432 \
  postgres:15

# Create tables (run migrations)
python -m alembic upgrade head
```

### 4. Initialize Redis

```bash
# Using Docker
docker run -d \
  --name smart-interview-cache \
  -p 6379:6379 \
  redis:7
```

---

## Database Migration

### 1. Create Migration Script

Create `app/database/init_db.py`:

```python
"""Initialize database schema."""

import asyncio
import logging
from app.database.connection import async_engine
from app.database.models import Base

logger = logging.getLogger(__name__)

async def init_database():
    """Create all tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")

if __name__ == "__main__":
    asyncio.run(init_database())
```

### 2. Run Migration

```bash
python -m app.database.init_db
```

### 3. Verify Schema

```bash
psql -U postgres -d smart_interview -c "\dt"
```

---

## Service Layer Updates

### 1. Create Repository Pattern

Create `app/database/repository.py`:

```python
"""Generic repository pattern for database access."""

from typing import Generic, TypeVar, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')

class Repository(Generic[T]):
    """Base repository for CRUD operations."""
    
    def __init__(self, session: AsyncSession, model: type[T]):
        self.session = session
        self.model = model
    
    async def get_by_id(self, id: str) -> Optional[T]:
        """Get record by ID."""
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalars().first()
    
    async def list(self, skip: int = 0, limit: int = 20) -> List[T]:
        """List records with pagination."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def create(self, obj: T) -> T:
        """Create new record."""
        self.session.add(obj)
        await self.session.flush()
        return obj
    
    async def update(self, obj: T) -> T:
        """Update existing record."""
        self.session.add(obj)
        await self.session.flush()
        return obj
    
    async def delete(self, id: str) -> bool:
        """Delete record."""
        obj = await self.get_by_id(id)
        if obj:
            await self.session.delete(obj)
            await self.session.flush()
            return True
        return False
```

### 2. Update ResumeService

The service layer should:
- Use the repository pattern for database operations
- Implement caching with cache-aside pattern
- Handle pagination
- Log all operations

Example structure:

```python
class ResumeService:
    def __init__(self, db_session: AsyncSession, cache):
        self.repo = Repository(db_session, Resume)
        self.cache = cache
    
    async def get_resume(self, resume_id: str) -> Optional[Resume]:
        # 1. Check cache
        cached = await self.cache.cache_get_json(resume_cache_key(resume_id))
        if cached:
            return Resume(**cached)
        
        # 2. Query database
        resume = await self.repo.get_by_id(resume_id)
        if resume:
            # 3. Cache for 1 hour
            await self.cache.cache_set_json(
                resume_cache_key(resume_id),
                resume.to_dict(),
                ttl=3600
            )
        return resume
    
    async def list_resumes(self, skip: int = 0, limit: int = 20):
        # Always query database for list (never cache full list)
        return await self.repo.list(skip, limit)
```

---

## API Implementation

### 1. Consolidated Endpoints

Create `app/api/v1/resumes.py`:

```python
"""Resume endpoints (consolidated)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from app.database.connection import get_async_session
from app.schemas.resume import ResumeCreateRequest, ResumeResponse
from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

router = APIRouter(prefix="/resumes", tags=["resumes"])

@router.post("", response_model=ResumeResponse)
async def create_resume(
    data: ResumeCreateRequest,
    session = Depends(get_async_session)
):
    """Create/upload resume."""
    service = ResumeService(session)
    resume = await service.create_resume(data)
    return resume

@router.get("", response_model=list[ResumeResponse])
async def list_resumes(
    skip: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    session = Depends(get_async_session)
):
    """List resumes with pagination."""
    service = ResumeService(session)
    return await service.list_resumes(skip, limit)

@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: str,
    session = Depends(get_async_session)
):
    """Get single resume."""
    service = ResumeService(session)
    resume = await service.get_resume(resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume
```

### 2. Response Envelope

Create middleware to wrap all responses:

```python
"""Response envelope middleware."""

@app.middleware("http")
async def response_envelope(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Wrap response
    body = b''
    async for chunk in response.body_iterator:
        body += chunk
    
    return JSONResponse({
        "status": "success" if response.status_code < 400 else "error",
        "data": json.loads(body),
        "meta": {
            "timing": {"total_ms": round(process_time * 1000, 2)},
            "request_id": request.headers.get("X-Request-ID"),
        }
    }, status_code=response.status_code)
```

---

## Caching Strategy

### 1. Cache Invalidation on Write

```python
async def update_resume(resume_id: str, data: ResumeUpdateRequest):
    # Update database
    resume = await self.repo.update(resume_id, data)
    
    # Invalidate cache
    await self.cache.cache_delete(resume_cache_key(resume_id))
    await self.cache.cache_delete_pattern(f"matches:*:{resume_id}")
    
    return resume
```

### 2. Cache Warming

```python
async def warm_cache():
    """Pre-load hot data into cache."""
    jobs = await job_repo.list_recent(limit=100)
    for job in jobs:
        await cache.cache_set_json(
            job_cache_key(job.id),
            job.to_dict(),
            ttl=CACHE_TTL_JOB
        )
```

### 3. Cache Monitoring

```python
@app.get("/metrics/cache")
async def cache_metrics():
    """Monitor cache performance."""
    client = await get_redis()
    info = await client.info("stats")
    return {
        "hits": info.get("keyspace_hits", 0),
        "misses": info.get("keyspace_misses", 0),
        "memory_used_mb": info.get("used_memory", 0) / 1024 / 1024,
    }
```

---

## Testing & Validation

### 1. Unit Tests

```python
"""Test services with database."""

import pytest
from app.services.resume_service import ResumeService
from app.database.models import Resume

@pytest.mark.asyncio
async def test_resume_creation(db_session):
    service = ResumeService(db_session)
    data = ResumeCreateRequest(
        name="John Doe",
        email="john@example.com",
        raw_text="Senior Python Developer..."
    )
    resume = await service.create_resume(data)
    assert resume.id
    assert resume.name == "John Doe"

@pytest.mark.asyncio
async def test_resume_caching(db_session, cache):
    service = ResumeService(db_session, cache)
    resume = await service.get_resume("test-id")
    # Verify cached on second call
    cached = await cache.cache_get_json(f"resume:test-id")
    assert cached is not None
```

### 2. Integration Tests

```python
"""Test full API flow."""

@pytest.mark.asyncio
async def test_resume_upload_and_match(client):
    # Upload resume
    response = await client.post("/api/v1/resumes", json={
        "name": "Jane Smith",
        "email": "jane@example.com",
        "raw_text": "...",
    })
    assert response.status_code == 200
    resume_id = response.json()["data"]["id"]
    
    # Get resume
    response = await client.get(f"/api/v1/resumes/{resume_id}")
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Jane Smith"
```

### 3. Performance Tests

```bash
# Load testing with locust
locust -f tests/load_test.py --host=http://localhost:8000
```

---

## Deployment

### 1. Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Docker Compose

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://user:pass@db:5432/smart_interview
      REDIS_URL: redis://cache:6379/0
    depends_on:
      - db
      - cache
  
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: smart_interview
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  cache:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### 3. Kubernetes Deployment

See [SCALABLE_ARCHITECTURE.md](SCALABLE_ARCHITECTURE.md) for full K8s manifests.

---

## Checklist

- [ ] PostgreSQL installed and running
- [ ] Redis installed and running
- [ ] Database schema created
- [ ] Services updated to use database
- [ ] API endpoints consolidated
- [ ] Caching implemented
- [ ] Pagination added
- [ ] Authentication configured
- [ ] Rate limiting implemented
- [ ] Logging configured
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Load tests completed
- [ ] Docker images built
- [ ] Kubernetes manifests created
- [ ] Monitoring configured
- [ ] Documentation updated

---

## Next Steps

1. **Phase 2**: Async workers (Celery) for embeddings computation
2. **Phase 3**: Distributed tracing (OpenTelemetry) for debugging
3. **Phase 4**: Automated scaling policies and health checks
4. **Phase 5**: Advanced caching (Redis Cluster, memcached)

---

## Support & Troubleshooting

### Connection Issues

```bash
# Test database connection
python -c "import asyncpg; asyncio.run(asyncpg.connect('postgresql://...'))"

# Test Redis connection
redis-cli -h localhost ping
```

### Performance Issues

```bash
# Monitor database connections
psql -d smart_interview -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"

# Monitor cache memory
redis-cli info memory
```

### Debug Logging

Set `DEBUG=true` and `LOG_LEVEL=DEBUG` in environment to enable verbose logging.
