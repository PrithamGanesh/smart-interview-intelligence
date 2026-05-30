"""Candidate-job fit scoring."""

from app.core.config import get_settings
from app.ml.embeddings import cosine_similarity_score
from app.models.domain import JobDescription, Resume


def score_candidate_fit(resume: Resume, job: JobDescription) -> dict[str, object]:
    """Score a resume against a job description using blueprint weights."""
    settings = get_settings()
    weights = settings.ranking_weights
    candidate_skills = set(resume.skills)
    required = set(job.required_skills)
    preferred = set(job.preferred_skills)

    matched_required = sorted(candidate_skills & required)
    missing_required = sorted(required - candidate_skills)
    matched_preferred = sorted(candidate_skills & preferred)
    missing_preferred = sorted(preferred - candidate_skills)

    skill_score = len(matched_required) / len(required) if required else 1.0
    experience_score = (
        min(resume.years_experience / job.min_years_experience, 1.0)
        if job.min_years_experience > 0
        else 1.0
    )
    education_score = score_education(resume.education, job.raw_text)
    project_score = 1.0 if resume.projects else project_signal_score(resume.raw_text)
    certification_score = 1.0 if resume.certifications else certification_signal_score(resume.raw_text)
    similarity_score = cosine_similarity_score(resume.raw_text, job.raw_text)

    fit_score = round(
        (
            skill_score * weights.skill_match
            + experience_score * weights.experience
            + education_score * weights.education
            + project_score * weights.projects
            + certification_score * weights.certifications
        )
        * 100,
        2,
    )
    recommendation = classify_fit(fit_score, missing_required)

    return {
        "candidate_id": resume.id,
        "candidate_name": resume.candidate_name,
        "job_id": job.id,
        "job_title": job.title,
        "fit_score": fit_score,
        "score": fit_score,
        "match_score": similarity_score,
        "similarity_score": similarity_score,
        "recommendation": recommendation,
        "matched_required_skills": matched_required,
        "missing_required_skills": missing_required,
        "matched_preferred_skills": matched_preferred,
        "missing_preferred_skills": missing_preferred,
        "skill_score": round(skill_score * 100, 2),
        "experience_score": round(experience_score * 100, 2),
        "education_score": round(education_score * 100, 2),
        "project_score": round(project_score * 100, 2),
        "certification_score": round(certification_score * 100, 2),
        "candidate_years_experience": resume.years_experience,
        "required_years_experience": job.min_years_experience,
    }


def classify_fit(score: float, missing_required: list[str]) -> str:
    """Convert a score into a recruiter-friendly recommendation."""
    if score >= 85 and not missing_required:
        return "strong_fit"
    if score >= 70:
        return "good_fit"
    if score >= 50:
        return "possible_fit"
    return "low_fit"


def score_education(education: str, job_text: str) -> float:
    """Score education against common job education requirements."""
    candidate = (education or "").lower()
    job = (job_text or "").lower()
    if not job or not any(token in job for token in ("b.tech", "bachelor", "master", "m.tech", "phd", "ph.d", "degree")):
        return 1.0 if candidate else 0.6
    if "ph" in job:
        return 1.0 if "ph" in candidate or "doctor" in candidate else 0.3
    if "master" in job or "m.tech" in job:
        return 1.0 if any(token in candidate for token in ("master", "m.tech", "ph", "doctor")) else 0.5
    if any(token in candidate for token in ("b.tech", "bachelor", "b.e", "master", "m.tech", "ph", "doctor")):
        return 1.0
    return 0.4


def project_signal_score(text: str) -> float:
    """Infer project evidence from resume text."""
    value = (text or "").lower()
    if "project" in value or "portfolio" in value or "built" in value:
        return 0.8
    return 0.2


def certification_signal_score(text: str) -> float:
    """Infer certification evidence from resume text."""
    value = (text or "").lower()
    if "certified" in value or "certification" in value or "certificate" in value:
        return 0.8
    return 0.2
