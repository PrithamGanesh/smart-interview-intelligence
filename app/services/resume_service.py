"""Resume ingestion and extraction service."""

from uuid import uuid4

from app.database.store import store
from app.models.domain import Resume
from app.schemas.resume import ResumeCreate
from app.services.resume_parser import extract_text_from_bytes, parse_resume_text


class ResumeService:
    """Coordinates resume ingestion and retrieval."""

    def create_resume(self, payload: ResumeCreate) -> Resume:
        candidate_name = payload.name or payload.candidate_name
        profile = parse_resume_text(
            payload.resume_text,
            candidate_name=candidate_name.strip() if candidate_name else None,
            resume_path=payload.resume_path,
        )
        if payload.email:
            profile["email"] = payload.email
        if payload.education:
            profile["education"] = payload.education
        return self._save_profile(profile)

    def create_resume_from_upload(self, content: bytes, filename: str) -> Resume:
        text = extract_text_from_bytes(content, filename)
        profile = parse_resume_text(text, resume_path=filename)
        return self._save_profile(profile)

    def _save_profile(self, profile: dict[str, object]) -> Resume:
        resume = Resume(
            id=str(uuid4()),
            name=str(profile["name"]),
            email=profile.get("email"),
            raw_text=str(profile["raw_text"]),
            skills=list(profile["skills"]),
            experience=float(profile["experience"]),
            education=str(profile["education"]),
            projects=list(profile["projects"]),
            certifications=list(profile["certifications"]),
            resume_path=profile.get("resume_path"),
        )
        return store.save_resume(resume)

    def get_resume(self, resume_id: str) -> Resume:
        return store.get_resume(resume_id)

    def list_resumes(self) -> list[Resume]:
        return store.list_resumes()


resume_service = ResumeService()
