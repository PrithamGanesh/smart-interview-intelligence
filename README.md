# Smart Interview Intelligence

Smart Interview Intelligence is organized as a Python project with a service layer, machine learning workspace, tests, documentation, deployment assets, and monitoring configuration.

## Project Structure

```text
app/
  api/
  core/
  database/
  models/
  schemas/
  services/
  ml/
  utils/
  main.py
training/
  data/
  notebooks/
  train.py
  evaluate.py
tests/
docker/
monitoring/
docs/
.github/workflows/
```

## Features

- Accept resume uploads through `POST /api/v1/resume/upload`.
- Validate uploaded resume type/size before parsing `.pdf`, `.txt`, or `.docx` files.
- Parse candidate name, email, skills, experience, education, projects, and certifications while masking PII in stored resume text.
- Analyze job descriptions through `POST /api/v1/job/create`.
- Extract skills with a versioned taxonomy, alias normalization, and soft-skill support.
- Match resumes and jobs using Sentence Transformers when available, with cached offline TF-IDF fallback.
- Rank candidates using configured blueprint weights: skill match 40%, experience 25%, education 10%, projects 15%, certifications 10%.
- Identify skill gaps with severity, generate deduplicated/cached interview questions, and predict candidate success probability with feature contributions.
- Expose recruiter dashboards, request IDs, optional API key protection, rate limiting, versioned health checks, and Prometheus-compatible metrics.

## Getting Started

Install runtime dependencies:

```bash
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Open the interactive API docs at `http://127.0.0.1:8000/docs`.

## API Overview

- `POST /api/v1/resume/upload`
- `GET /api/v1/resume/{id}`
- `DELETE /api/v1/resume/{id}`
- `GET /api/v1/candidates`
- `GET /api/v1/candidates/{id}/gap?job_id=...`
- `POST /api/v1/job/create`
- `GET /api/v1/job/{id}`
- `GET /api/v1/jobs`
- `POST /api/v1/match`
- `POST /api/v1/rank`
- `POST /api/v1/questions`
- `GET /api/v1/questions/{job_id}`
- `POST /api/v1/predict-success`
- `GET /api/v1/taxonomy/skills`
- `GET /api/v1/health`
- `GET /api/v1/dashboard`

Legacy plural endpoints under `/api/v1/resumes` and `/api/v1/jobs` remain available for local JSON workflows.

Copy `.env.example` for local configuration. Set `API_KEY` to require an `X-API-Key` header on versioned API routes.

## Docker

```bash
docker compose -f docker/docker-compose.yml up --build
```
