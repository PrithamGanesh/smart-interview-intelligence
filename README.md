# Smart Interview Intelligence

AI-assisted resume screening and candidate ranking system with semantic matching, skill gap analysis, and interview question generation. Built with FastAPI, Sentence Transformers, and XGBoost.

**Health Score**: 7.5/10 | **Status**: MVP-ready, production improvements needed

## Quick Start

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open API docs at `http://127.0.0.1:8000/docs`

## Features

- **Resume Processing**: Upload & parse `.pdf`, `.txt`, `.docx` with PII masking
- **Job Analysis**: Extract skills, requirements, and semantic job embeddings
- **Resume-Job Matching**: Semantic similarity via Sentence Transformers + TF-IDF fallback
- **Candidate Ranking**: Multi-dimensional scoring (skills 40%, experience 25%, education 10%, projects 15%, certs 10%)
- **Skill Gaps**: Identify missing skills with severity levels
- **Interview Questions**: AI-generated, deduplicated, cached questions
- **Success Prediction**: XGBoost model with heuristic fallback
- **Recruiter Dashboard**: Top candidates, match quality, rankings
- **Monitoring**: Prometheus metrics + Grafana visualization
- **API Protection**: Optional API key auth + rate limiting

## Project Structure

```
app/
  api/          # HTTP endpoints
  services/     # Business logic layer
  ml/           # Embeddings, scoring, ML models
  database/     # Data persistence abstractions
  models/       # Domain objects (Resume, Job)
  schemas/      # Pydantic request/response validation
  core/         # Config, exceptions, middleware
  utils/        # Helpers (text parsing, email extraction)
tests/          # Integration tests
docker/         # Docker Compose setup
monitoring/     # Prometheus + Grafana
```

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/resume/upload` | Upload resume file |
| GET | `/api/v1/candidates` | List candidates |
| GET | `/api/v1/candidates/{id}/gap` | Skill gaps for candidate |
| POST | `/api/v1/job/create` | Create job description |
| GET | `/api/v1/jobs` | List jobs |
| POST | `/api/v1/rank` | Rank candidates for job |
| POST | `/api/v1/match` | Match specific resume to job |
| POST | `/api/v1/questions` | Generate interview questions |
| POST | `/api/v1/predict-success` | Predict candidate success |
| GET | `/api/v1/dashboard` | Recruiter dashboard |

## Configuration

Copy `.env.example` and set variables:

```bash
API_KEY=your-key          # Optional, enables X-API-Key header requirement
DB_URL=postgresql://...   # PostgreSQL connection (dev: in-memory)
REDIS_URL=redis://...     # Redis cache URL
CORS_ORIGINS=*            # CORS allowed origins
```

## Docker Deployment

```bash
docker compose -f docker/docker-compose.yml up --build
```

Includes: FastAPI app, PostgreSQL, Redis, Prometheus, Grafana

## Known Limitations

### Critical Issues (Pre-Production)
- **No Pagination**: List endpoints return all results. Use limits for large datasets.
- **No Authentication**: API is completely open. Add JWT/OAuth2 before production.
- **In-Memory Storage**: Data lost on restart (dev only). Migrate to PostgreSQL for persistence.
- **Race Conditions**: Global state not thread-safe. Use database locking for concurrent writes.
- **Silent Errors**: Exception handling swallows logs. Need structured logging.

### Performance Considerations
- **Model Cold Start**: 5-30s on first request (Sentence Transformers). Pre-load models on startup.
- **Dashboard O(N*M)**: Scoring all candidates for all jobs. Add pagination and caching.
- **N+1 Queries**: Each list operation queries per item. Use eager loading (SQLAlchemy `selectinload`).
- **No Batch Operations**: Ranking 1000 resumes = 1000 DB writes. Batch insert 100 at a time.
- **Cache Misses**: Embeddings recalculated per request. Cache vectors, not just scores.

### Endpoint Duplication (Confusing)
- `POST /resumes` vs `POST /resume/upload`
- `GET /candidates` vs `GET /resumes`
- Plan to consolidate to single `/candidates` and `/jobs` paths

## Production Readiness

### ✅ Production-Ready
- Clean architecture with service layer
- Graceful fallbacks (embeddings, ML models)
- Docker Compose with monitoring stack
- Comprehensive API design
- Pydantic validation

### ⚠️ Before Production Deploy
1. **Immediate** (1-2 days):
   - Add authentication (API key or JWT)
   - Implement pagination for list endpoints
   - Add structured logging (Python logging or loguru)
   - Consolidate duplicate endpoints
   - Fix education scoring logic edge cases

2. **Short-term** (3-5 days):
   - Migrate to PostgreSQL (setup provided)
   - Add comprehensive unit tests (currently: 1 integration test)
   - Pre-load ML models on startup
   - Implement batch ranking operations

3. **Medium-term** (1-2 weeks):
   - Add distributed tracing (OpenTelemetry)
   - Set up monitoring alerts
   - Load test with 10,000 candidates
   - Document deployment runbooks

## Testing

```bash
# Run existing tests
pytest tests/ -v

# Key gaps:
# - No unit tests for services, ML, utilities
# - No edge case tests (empty text, invalid inputs)
# - No concurrent write tests
# Target: 70%+ code coverage
```

## Contributing

1. Clone repo and install dev dependencies
2. Create feature branch
3. Add tests for new functionality
4. Run `pytest tests/` to verify
5. Submit PR with test coverage

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| API hangs on first request | Model cold start | Pre-load models in app startup |
| High memory usage | Embeddings cached indefinitely | Use ExpiringDict with TTL |
| Slow ranking | N+1 queries | Use eager loading for relations |
| 404 on duplicate endpoints | Endpoint confusion | Use `/api/v1/candidates` path |
| Silent errors in logs | Exception swallowing | Add logging to exception handlers |

## Monitoring

Dashboard available at: `http://localhost:3000` (Grafana)  
Prometheus metrics at: `http://localhost:9090`

Key metrics:
- `api_request_count` - Request volume
- `api_request_latency_seconds` - Response time
- `embedding_cache_hits` - Cache effectiveness
- Health: `GET /health` → `{"status": "ok"}`
