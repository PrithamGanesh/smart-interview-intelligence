from fastapi.testclient import TestClient

from app.database.store import store
from app.main import app


def test_dashboard_ui_is_served_at_root():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Smart Interview Intelligence" in response.text
    assert 'id="save-resume"' in response.text
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert "'unsafe-eval'" not in response.headers["content-security-policy"]


def test_blueprint_workflow():
    client = TestClient(app)

    resume = client.post(
        "/api/v1/resumes",
        json={
            "name": "John Doe",
            "email": "john@example.com",
            "resume_text": "John Doe\njohn@example.com\nB.Tech\n3 years experience with Python, FastAPI, Docker, AWS. Projects: interview platform. Certified AWS.",
        },
    )
    assert resume.status_code == 201

    job = client.post(
        "/api/v1/job/create",
        json={
            "title": "Python Developer",
            "description": "Need Python developer with FastAPI, Docker, AWS and 2 years experience.",
        },
    )
    assert job.status_code == 201

    candidate_id = resume.json()["id"]
    job_id = job.json()["id"]

    match = client.post("/api/v1/match", json={"candidate_id": candidate_id, "job_id": job_id})
    assert match.status_code == 200
    assert match.json()["score"] >= 0

    ranking = client.post("/api/v1/rank", json={"job_id": job_id})
    assert ranking.status_code == 200
    assert ranking.json()["rankings"][0]["rank"] == 1

    questions = client.post("/api/v1/questions", json={"candidate_id": candidate_id, "job_id": job_id, "count": 2})
    assert questions.status_code == 200
    assert len(questions.json()["questions"]) == 2

    prediction = client.post("/api/v1/predict-success", json={"candidate_id": candidate_id, "job_id": job_id})
    assert prediction.status_code == 200
    assert prediction.json()["success_probability"] >= 0
    assert prediction.json()["feature_contributions"]["skill_score"] >= 0

    gaps = client.get(f"/api/v1/candidates/{candidate_id}/gap", params={"job_id": job_id})
    assert gaps.status_code == 200
    assert "gap_details" in gaps.json()

    cached_questions = client.get(f"/api/v1/questions/{job_id}")
    assert cached_questions.status_code == 200
    assert len(cached_questions.json()["questions"]) == 2

    taxonomy = client.get("/api/v1/taxonomy/skills")
    assert taxonomy.status_code == 200
    assert taxonomy.json()["count"] >= 40

    candidates = client.get("/api/v1/candidates")
    assert candidates.status_code == 200
    assert any(candidate["id"] == candidate_id for candidate in candidates.json())


def test_resume_upload_validation_rejects_unsupported_file_type():
    client = TestClient(app)

    response = client.post(
        "/api/v1/resume/upload",
        files={"file": ("resume.exe", b"not a resume", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "Unsupported resume file type" in response.json()["detail"]


def test_job_experience_range_and_skill_alias_normalization():
    client = TestClient(app)

    response = client.post(
        "/api/v1/job/create",
        json={
            "title": "ML Platform Engineer",
            "description": "Need python3, GenAI, LLMs, k8s and 3-5 years experience.",
            "preferred_skills": ["Amazon Web Services"],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["experience"] == 3
    assert payload["max_years_experience"] == 5
    assert {"Python", "Generative AI", "Large Language Models", "Kubernetes"}.issubset(set(payload["skills"]))
    assert payload["preferred_skills"] == ["AWS"]


def test_resume_text_is_masked_at_rest_and_can_be_erased():
    client = TestClient(app)

    response = client.post(
        "/api/v1/resumes",
        json={
            "name": "Priya Sharma",
            "email": "priya@example.com",
            "resume_text": "Priya Sharma\npriya@example.com\n+1 555 123 4567\nB.Tech\n4 years experience with Python and AWS.",
        },
    )

    assert response.status_code == 201
    resume_id = response.json()["id"]
    assert "priya@example.com" not in response.json()["raw_text"]
    stored = store.get_resume(resume_id)
    assert "priya@example.com" not in stored.raw_text
    assert "+1 555 123 4567" not in stored.raw_text

    deleted = client.delete(f"/api/v1/resume/{resume_id}")
    assert deleted.status_code == 204
    missing = client.get(f"/api/v1/resume/{resume_id}")
    assert missing.status_code == 404
