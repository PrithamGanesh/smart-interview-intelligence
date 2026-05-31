"""Storage abstraction.

This in-memory repository keeps the project runnable out of the box. The service
layer depends on this module only, so replacing it with Postgres or another
production database is straightforward.
"""

from app.core.exceptions import NotFoundError
from app.models.domain import JobDescription, Resume
from typing import Optional


class InMemoryStore:
    """Simple repository for candidates, jobs, and match results.

    The production target is PostgreSQL through SQLAlchemy models in
    app.models.database. This store keeps tests and local demos runnable without
    external services.
    """

    def __init__(self) -> None:
        self._resumes: dict[str, Resume] = {}
        self._jobs: dict[str, JobDescription] = {}
        self._match_results: dict[tuple[str, str], dict[str, object]] = {}
        self._question_bank: dict[str, list[str]] = {}

    def save_resume(self, resume: Resume) -> Resume:
        self._resumes[resume.id] = resume
        return resume

    def get_resume(self, resume_id: str) -> Resume:
        try:
            return self._resumes[resume_id]
        except KeyError as exc:
            raise NotFoundError(f"Resume '{resume_id}' was not found.") from exc

    def list_resumes(self) -> list[Resume]:
        return sorted(self._resumes.values(), key=lambda item: item.created_at, reverse=True)

    def delete_resume(self, resume_id: str) -> None:
        if resume_id not in self._resumes:
            raise NotFoundError(f"Resume '{resume_id}' was not found.")
        del self._resumes[resume_id]
        for key in [key for key in self._match_results if key[0] == resume_id]:
            del self._match_results[key]

    def save_job(self, job: JobDescription) -> JobDescription:
        self._jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> JobDescription:
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise NotFoundError(f"Job description '{job_id}' was not found.") from exc

    def list_jobs(self) -> list[JobDescription]:
        return sorted(self._jobs.values(), key=lambda item: item.created_at, reverse=True)

    def save_match_result(self, candidate_id: str, job_id: str, score: float, rank: Optional[int] = None) -> dict[str, object]:
        result = {
            "candidate_id": candidate_id,
            "job_id": job_id,
            "score": score,
            "rank": rank,
        }
        self._match_results[(candidate_id, job_id)] = result
        return result

    def list_match_results(self) -> list[dict[str, object]]:
        return list(self._match_results.values())

    def save_questions(self, job_id: str, questions: list[str]) -> list[str]:
        existing = self._question_bank.setdefault(job_id, [])
        for question in questions:
            if question not in existing:
                existing.append(question)
        return existing

    def get_questions(self, job_id: str) -> list[str]:
        return list(self._question_bank.get(job_id, []))


store = InMemoryStore()
