"""Candidate analysis, ranking, and dashboard service."""

from __future__ import annotations

from collections import Counter
from typing import Optional

from app.core.config import get_settings
from app.database.store import store
from app.ml.scoring import score_candidate_fit
from app.ml.success_predictor import predict_success_probability
from app.schemas.analysis import ExtractionResponse
from app.services.job_service import job_service
from app.services.resume_service import resume_service
from app.utils.text import extract_keywords, extract_skills, extract_years_experience


class AnalysisService:
    """High-level intelligence workflows for recruiters."""

    def extract_profile(self, text: str) -> ExtractionResponse:
        return ExtractionResponse(
            skills=extract_skills(text),
            years_experience=extract_years_experience(text),
            keywords=extract_keywords(text),
        )

    def predict_fit(self, candidate_id: str, job_id: str) -> dict[str, object]:
        resume = resume_service.get_resume(candidate_id)
        job = job_service.get_job(job_id)
        fit = score_candidate_fit(resume, job)
        store.save_match_result(candidate_id, job_id, float(fit["score"]))
        return fit

    def match(self, candidate_id: str, job_id: str) -> dict[str, object]:
        fit = self.predict_fit(candidate_id, job_id)
        return {
            "candidate_id": candidate_id,
            "job_id": job_id,
            "score": fit["similarity_score"],
            "match_score": fit["similarity_score"],
            "similarity_score": fit["similarity_score"],
        }

    def rank_candidates(self, job_id: str) -> dict[str, object]:
        job = job_service.get_job(job_id)
        rankings = [score_candidate_fit(resume, job) for resume in resume_service.list_resumes()]
        rankings.sort(key=lambda item: item["fit_score"], reverse=True)
        for index, item in enumerate(rankings, start=1):
            store.save_match_result(str(item["candidate_id"]), job_id, float(item["score"]), rank=index)
        return {
            "job_id": job.id,
            "job_title": job.title,
            "rankings": rankings,
        }

    def rank_candidates_blueprint(self, job_id: str, candidate_ids: Optional[list[str]] = None) -> dict[str, object]:
        job = job_service.get_job(job_id)
        candidates = resume_service.list_resumes()
        if candidate_ids:
            allowed = set(candidate_ids)
            candidates = [candidate for candidate in candidates if candidate.id in allowed]
        scored = [score_candidate_fit(candidate, job) for candidate in candidates]
        scored.sort(key=lambda item: item["score"], reverse=True)
        rankings = []
        for rank, item in enumerate(scored, start=1):
            store.save_match_result(str(item["candidate_id"]), job_id, float(item["score"]), rank=rank)
            rankings.append(
                {
                    "rank": rank,
                    "candidate_id": item["candidate_id"],
                    "name": item["candidate_name"],
                    "score": item["score"],
                    "feature_scores": {
                        "skill_match": item["skill_score"],
                        "experience": item["experience_score"],
                        "education": item["education_score"],
                        "projects": item["project_score"],
                        "certifications": item["certification_score"],
                    },
                }
            )
        return {"job_id": job.id, "rankings": rankings}

    def identify_skill_gaps(self, candidate_id: str, job_id: str) -> dict[str, object]:
        fit = self.predict_fit(candidate_id, job_id)
        experience_gap = max(
            float(fit["required_years_experience"]) - float(fit["candidate_years_experience"]),
            0.0,
        )
        priority_gaps = list(fit["missing_required_skills"])
        if experience_gap:
            priority_gaps.append(f"{experience_gap:g} years additional experience")
        return {
            "candidate_id": candidate_id,
            "job_id": job_id,
            "missing_required_skills": fit["missing_required_skills"],
            "missing_preferred_skills": fit["missing_preferred_skills"],
            "missing_skills": fit["missing_required_skills"],
            "experience_gap_years": round(experience_gap, 2),
            "priority_gaps": priority_gaps,
        }

    def generate_interview_questions(
        self,
        candidate_id: Optional[str] = None,
        job_id: Optional[str] = None,
        count: Optional[int] = None,
        skills: Optional[list[str]] = None,
    ) -> dict[str, object]:
        settings = get_settings()
        limit = min(count or settings.default_question_count, settings.max_generated_questions)
        questions: list[str] = []

        if candidate_id and job_id:
            resume = resume_service.get_resume(candidate_id)
            job = job_service.get_job(job_id)
            fit = score_candidate_fit(resume, job)
            skills = skills or list(fit["matched_required_skills"]) or resume.skills
            for skill in fit["missing_required_skills"]:
                questions.append(f"Describe how you would approach a production task that requires {skill}.")
            if fit["candidate_years_experience"] < fit["required_years_experience"]:
                questions.append("How have you ramped up quickly when a role required more experience than you initially had?")
            questions.append(f"What would your first 30 days look like as a {job.title}?")
        else:
            resume = None
            job = None
            skills = skills or []

        for skill in skills:
            questions.extend(question_templates(skill))

        questions.extend(
            [
                "Tell me about a time you handled ambiguous requirements from stakeholders.",
                "Which part of your background best demonstrates impact for this role?",
            ]
        )

        return {
            "candidate_id": resume.id if resume else candidate_id or "",
            "job_id": job.id if job else job_id or "",
            "questions": questions[:limit],
        }

    def predict_success(
        self,
        candidate_id: Optional[str] = None,
        job_id: Optional[str] = None,
        skill_score: Optional[float] = None,
        experience: Optional[float] = None,
        education: Optional[str] = None,
    ) -> dict[str, object]:
        if candidate_id and job_id:
            fit = self.predict_fit(candidate_id, job_id)
            resume = resume_service.get_resume(candidate_id)
            skill_score = float(fit["skill_score"])
            experience = resume.experience
            education = resume.education
        result = predict_success_probability(
            skill_score=skill_score or 0.0,
            experience=experience or 0.0,
            education=education or "",
        )
        result["candidate_id"] = candidate_id
        result["job_id"] = job_id
        return result

    def recruiter_dashboard(self, job_id: Optional[str] = None) -> dict[str, object]:
        resumes = resume_service.list_resumes()
        jobs = [job_service.get_job(job_id)] if job_id else job_service.list_jobs()
        scored: list[dict[str, object]] = []
        for job in jobs:
            scored.extend(score_candidate_fit(resume, job) for resume in resumes)

        recommendation_counts = Counter(str(item["recommendation"]) for item in scored)
        all_scores = [float(item["fit_score"]) for item in scored]
        skill_counts = Counter(skill for resume in resumes for skill in resume.skills)

        scored.sort(key=lambda item: item["fit_score"], reverse=True)
        return {
            "total_candidates": len(resumes),
            "total_jobs": len(jobs),
            "average_fit_score": round(sum(all_scores) / len(all_scores), 2) if all_scores else 0.0,
            "recommendation_counts": dict(recommendation_counts),
            "top_candidates": scored[:5],
            "most_common_skills": [skill for skill, _ in skill_counts.most_common(10)],
        }


analysis_service = AnalysisService()


def question_templates(skill: str) -> list[str]:
    """Generate skill-template interview questions with LLM-ready phrasing."""
    normalized = skill.lower()
    if normalized == "fastapi":
        return [
            "Explain dependency injection in FastAPI.",
            "How would you structure authentication and validation in a FastAPI service?",
        ]
    if normalized == "docker":
        return [
            "How do Docker layers work?",
            "How would you reduce the size of a production Docker image?",
        ]
    if normalized == "python":
        return [
            "Explain how Python memory management works.",
            "How would you design a reliable background job in Python?",
        ]
    if normalized == "aws":
        return [
            "Which AWS services would you use for a scalable API deployment?",
            "How would you secure secrets and IAM permissions in AWS?",
        ]
    return [
        f"Walk me through a project where you used {skill} to solve a business problem.",
        f"What are common production pitfalls when working with {skill}?",
    ]
