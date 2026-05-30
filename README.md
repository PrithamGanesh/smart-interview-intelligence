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
- Parse candidate name, email, skills, experience, education, projects, and certifications.
- Analyze job descriptions through `POST /api/v1/job/create`.
- Extract skills with a master skills database that can be backed by spaCy PhraseMatcher.
- Match resumes and jobs using Sentence Transformers when available, with an offline TF-IDF fallback.
- Rank candidates using configured blueprint weights: skill match 40%, experience 25%, education 10%, projects 15%, certifications 10%.
- Identify skill gaps, generate interview questions, and predict candidate success probability.
- Expose recruiter dashboards and Prometheus-compatible metrics.

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
- `POST /api/v1/job/create`
- `GET /api/v1/job/{id}`
- `POST /api/v1/match`
- `POST /api/v1/rank`
- `POST /api/v1/questions`
- `POST /api/v1/predict-success`
- `GET /api/v1/dashboard`

Legacy plural endpoints under `/api/v1/resumes` and `/api/v1/jobs` remain available for local JSON workflows.

## Docker

```bash
docker compose -f docker/docker-compose.yml up --build
```
