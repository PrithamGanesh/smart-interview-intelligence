"""Job description ingestion service."""

from uuid import uuid4

from app.database.store import store
from app.models.domain import JobDescription
from app.schemas.job import JobDescriptionCreate
from app.utils.text import extract_experience_range, extract_skills, normalize_text, unique_sorted


class JobService:
    """Coordinates job description ingestion and retrieval."""

    def create_job(self, payload: JobDescriptionCreate) -> JobDescription:
        text = normalize_text(payload.description)
        extracted_skills = extract_skills(text)
        skills = unique_sorted(payload.skills or payload.required_skills) or extracted_skills
        preferred = unique_sorted(payload.preferred_skills)
        min_years = payload.experience
        max_years = payload.experience
        if min_years is None:
            min_years = payload.min_years_experience
        if min_years is None:
            min_years, max_years = extract_experience_range(text)
        if max_years is None:
            max_years = min_years

        job = JobDescription(
            id=str(uuid4()),
            title=payload.title.strip(),
            description=text,
            skills=skills,
            experience=min_years or 0.0,
            preferred=preferred,
            max_experience=max_years or min_years or 0.0,
        )
        return store.save_job(job)

    def get_job(self, job_id: str) -> JobDescription:
        return store.get_job(job_id)

    def list_jobs(self) -> list[JobDescription]:
        return store.list_jobs()


job_service = JobService()
