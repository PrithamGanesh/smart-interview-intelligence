from fastapi.testclient import TestClient

from app.main import app


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
