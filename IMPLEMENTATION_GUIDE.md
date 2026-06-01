# IMPLEMENTATION GUIDE - Apply Fixes to Production

## Overview
This guide shows how to apply the critical production fixes to your codebase. The changes are organized by priority and dependencies.

---

## PHASE 1: CRITICAL FIXES (Do First - Blocks Other Work)

### Fix 1: Add Thread-Safety to Store [30 min]

**File:** `app/database/store.py`

**What to do:**
1. Add imports for threading
2. Replace all mutable operations with lock-protected versions
3. Add pagination methods

**Key changes:**
```python
# ADD at top
import threading

class InMemoryStore:
    def __init__(self):
        # ... existing code ...
        self._resume_lock = threading.RLock()
        self._job_lock = threading.RLock()
        self._match_lock = threading.RLock()
        self._question_lock = threading.RLock()

    def save_resume(self, resume: Resume) -> Resume:
        with self._resume_lock:  # 🔧 ADD THIS LOCK
            self._resumes[resume.id] = resume
            return resume
    
    def list_resumes(self, limit: int = 100, offset: int = 0) -> tuple[list[Resume], int]:
        # 🔧 ADD THIS METHOD for pagination
        with self._resume_lock:
            sorted_resumes = sorted(...)
            total = len(sorted_resumes)
            paginated = sorted_resumes[offset : offset + limit]
            return paginated, total
    
    def batch_save_match_results(self, results: list[tuple]) -> list[dict]:
        # 🔧 ADD THIS METHOD for performance
        saved = []
        with self._match_lock:
            for candidate_id, job_id, score, rank in results:
                # ... batch save ...
```

**Testing:** Create test that launches 100 concurrent requests - should not crash

---

### Fix 2: Add Thread-Safe Middleware [20 min]

**File:** `app/main.py` (or create new `middleware.py`)

**What to do:**
1. Replace global `REQUEST_COUNT`, `REQUEST_LATENCY_SECONDS`, `RATE_BUCKETS` with thread-safe class
2. Fix GuardrailMiddleware to use thread-safe operations
3. Add error logging

**Key changes:**
```python
# Create ThreadSafeMetricsCollector class
class ThreadSafeMetricsCollector:
    def __init__(self):
        self.request_count = 0
        self.request_latencies: deque[float] = deque(maxlen=1000)
        self._lock = threading.RLock()
    
    def record_request(self, latency: float) -> None:
        with self._lock:
            self.request_count += 1
            self.request_latencies.append(latency)

# Create ThreadSafeRateLimiter class  
class ThreadSafeRateLimiter:
    def __init__(self, limit_per_minute: int = 120):
        self.buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.RLock()
    
    def is_allowed(self, client_id: str) -> bool:
        with self._lock:
            # Safe deque operations
            bucket = self.buckets[client_id]
            # ... check logic ...
            return True

# Update middleware
class GuardrailMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Use rate_limiter.is_allowed() instead of inline logic
        if not rate_limiter.is_allowed(client_id):
            return JSONResponse(status_code=429, ...)
```

---

### Fix 3: Fix Education Scoring Logic [25 min]

**File:** `app/ml/scoring.py`

**What to do:**
1. Replace substring matching with regex patterns
2. Fix education level hierarchy
3. Fix division by zero
4. Add input validation

**Key changes:**
```python
# ADD at top
EDUCATION_PATTERNS = {
    "phd": re.compile(r"\b(ph\.?d|doctorate)\b", re.IGNORECASE),
    "master": re.compile(r"\b(master|m\.?tech|m\.?s\.?)\b", re.IGNORECASE),
    "bachelor": re.compile(r"\b(bachelor|b\.?tech|b\.?e\.?)\b", re.IGNORECASE),
}

def score_candidate_fit(resume: Resume, job: JobDescription) -> dict:
    # ADD input validation
    if not resume or not job:
        raise ValueError("Resume and JobDescription required")
    
    # FIX: Handle empty skill lists
    candidate_skills = set(normalize_skills(resume.skills or []))
    required = set(normalize_skills(job.required_skills or []))
    
    # FIX: Skill score logic (division by zero)
    if required:
        skill_score = len(matched_required) / len(required)  # 0-1
    else:
        skill_score = 1.0  # No requirements = perfect
    
    # REPLACE score_education() call with new function
    education_score = score_education_fixed(resume.education, job.raw_text)
    
    # FIX: Return only "score" field (remove "fit_score")
    return {
        "candidate_id": resume.id,
        "score": fit_score,  # Single canonical field
        # ... rest unchanged ...
    }

def score_education_fixed(candidate_education: str, job_text: str) -> float:
    # Use regex patterns instead of substring matching
    candidate_level = _extract_education_level(candidate_education)
    job_level = _extract_education_level(job_text)
    
    if job_level is None:
        return 1.0 if candidate_level else 0.5
    
    if candidate_level is None:
        return 0.0
    
    # Level hierarchy: PhD (3) > Master (2) > Bachelor (1)
    if candidate_level >= job_level:
        return 1.0  # Meets or exceeds
    elif candidate_level == job_level - 1:
        return 0.5  # 1 level below
    else:
        return 0.0  # 2+ levels below

def _extract_education_level(text: str) -> int | None:
    text = (text or "").lower()
    if EDUCATION_PATTERNS["phd"].search(text):
        return 3
    if EDUCATION_PATTERNS["master"].search(text):
        return 2
    if EDUCATION_PATTERNS["bachelor"].search(text):
        return 1
    return None
```

**Testing:** 
- Test: PhD req + PhD candidate → 1.0
- Test: Masters req + Bachelor candidate → 0.5
- Test: No req + any education → 1.0

---

## PHASE 2: API IMPROVEMENTS (Do After Phase 1)

### Fix 4: Consolidate Routes [45 min]

**File:** `app/api/routes.py`

**What to do:**
1. Remove duplicate endpoints
2. Consolidate to single path structure
3. Add pagination Query parameters
4. Use `/api/v1` prefix consistently
5. Add missing DELETE endpoint for jobs

**Key changes:**
```python
# UPDATE imports
from fastapi import Query  # ADD this

# REMOVE these endpoints (duplicates):
# - @router.get("/candidates") - duplicate of /resumes
# - @router.post("/job/create") - duplicate of /jobs
# - @router.get("/job/{job_id}") - duplicate of /jobs/{job_id}
# - @router.get("/resume/{resume_id}") - duplicate of /resumes/{resume_id}

# UPDATE all endpoints to use /api/v1 prefix
router = APIRouter(prefix="/api/v1")

# UPDATE list endpoints to support pagination
@router.get("/resumes", response_model=list[ResumeResponse])
def list_resumes(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    resumes, total = resume_service.list_resumes(limit=limit, offset=offset)
    return resumes

# UPDATE ranking endpoint with pagination
@router.get("/jobs/{job_id}/rankings")
def rank_candidates(
    job_id: str,
    limit: int = Query(50, ge=1, le=200),
):
    return analysis_service.rank_candidates(job_id, limit=limit)

# ADD missing DELETE for jobs
@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: str) -> Response:
    job_service.delete_job(job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

---

### Fix 5: Update Services for Pagination [30 min]

**File:** `app/services/resume_service.py`, `app/services/job_service.py`, `app/services/analysis_service.py`

**What to do:**
1. Update list methods to support pagination
2. Update ranking method to support limit
3. Use batch_save_match_results for performance

**Key changes:**
```python
# In ResumeService
def list_resumes(self, limit: int = 100, offset: int = 0) -> tuple[list[Resume], int]:
    return store.list_resumes(limit=limit, offset=offset)

# In AnalysisService
def rank_candidates(self, job_id: str, limit: int = 50) -> dict[str, object]:
    job = job_service.get_job(job_id)
    resumes = resume_service.list_resumes(limit=limit)[0]  # Get paginated resumes
    rankings = [score_candidate_fit(resume, job) for resume in resumes]
    
    # Use batch save instead of individual calls
    batch_results = [
        (str(item["candidate_id"]), job_id, float(item["score"]), index)
        for index, item in enumerate(rankings, start=1)
    ]
    store.batch_save_match_results(batch_results)
    
    return {"rankings": rankings}

def recruiter_dashboard(self, job_id: Optional[str] = None, limit_top: int = 5):
    # REMOVE: Compute all N*M combinations
    # ADD: Return only relevant stats with pagination
    
    # Query paginated data instead of all
    resumes, _ = resume_service.list_resumes(limit=100)
    jobs = [job_service.get_job(job_id)] if job_id else job_service.list_jobs(limit=10)[0]
    
    # Only score first N resumes
    scored = [
        score_candidate_fit(resume, job)
        for job in jobs
        for resume in resumes[:100]
    ]
    
    return {
        "top_candidates": scored[:limit_top],
        # ... rest ...
    }
```

---

### Fix 6: Add Error Logging [20 min]

**File:** `app/services/resume_parser.py`

**What to do:**
1. Log failures instead of silently swallowing
2. Raise exceptions with context
3. Add logging module throughout

**Key changes:**
```python
import logging
logger = logging.getLogger(__name__)

def extract_text_from_bytes(content: bytes, filename: str = "resume.txt") -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        text = _extract_pdf_text(content)
        if not text:
            logger.warning(f"Failed to extract PDF text from {filename}")
            raise ValueError(f"Could not parse PDF: {filename}")
        return text

def _extract_pdf_text(content: bytes) -> str:
    try:
        import pdfplumber
        # ... extraction logic ...
    except Exception as exc:
        logger.warning(f"pdfplumber failed, trying PyMuPDF: {exc}")
    
    try:
        import fitz
        # ... extraction logic ...
    except Exception as exc:
        logger.error(f"Both PDF parsers failed: {exc}")
        raise ValueError("Unable to parse PDF") from exc
```

---

## PHASE 3: VERIFY & TEST

### Testing Checklist

- [ ] Unit test: Education scoring with all level combinations
- [ ] Unit test: Pagination works correctly (offset/limit)
- [ ] Concurrency test: 100 concurrent requests don't crash
- [ ] Integration test: All list endpoints support pagination
- [ ] Smoke test: `/health` endpoint responds
- [ ] Data consistency: Multiple requests produce consistent results
- [ ] Error handling: Invalid IDs return 404, not crashes

### Deployment Checklist

- [ ] Update Docker image with fixed code
- [ ] Run full test suite
- [ ] Stress test with 1000+ candidates and 100+ jobs
- [ ] Monitor logs for new warnings/errors
- [ ] Update API docs to reflect pagination parameters
- [ ] Tag release as `v0.2.0` (breaking change due to removed endpoints)

---

## DEPRECATED ENDPOINTS (Will be removed)

These endpoints will be removed in v0.2.0:

```
POST   /resume/upload          (use POST /resumes/upload)
GET    /candidates             (use GET /resumes)
GET    /resume/{id}            (use GET /resumes/{id})
DELETE /resume/{id}            (use DELETE /resumes/{id})
POST   /job/create             (use POST /jobs)
GET    /job/{id}               (use GET /jobs/{id})
```

**Migration path:** Update API clients to use consolidated endpoints before v0.2.0 release.

---

## ROLLBACK PLAN

If critical issues found in production:

1. Restore previous version from Docker image
2. Revert database schema if migrations applied
3. Keep thread-safe fixes (no rollback needed)
4. File incident report with changes that caused issue

---

## NEXT STEPS (Medium Priority)

After Phase 1-3 complete:

1. Implement PostgreSQL integration (replace in-memory store)
2. Add comprehensive logging framework
3. Create unit test suite (currently missing)
4. Implement response caching for expensive operations
5. Add database connection pooling
6. Create API rate limiting documentation
