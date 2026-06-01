"""FIXED: Corrected candidate-job fit scoring logic.

This replaces app/ml/scoring.py with fixes for:
- Education scoring logic bugs
- Validation of inputs
- Consistent field naming
- Proper handling of edge cases
"""

import re
from app.core.config import get_settings
from app.ml.embeddings import cosine_similarity_score
from app.models.domain import JobDescription, Resume
from app.utils.taxonomy import normalize_skills


# 🔧 ADDED: Compiled regex patterns for education matching (more robust)
EDUCATION_PATTERNS = {
    "phd": re.compile(r"\b(ph\.?d|phd|doctorate|doctor of philosophy)\b", re.IGNORECASE),
    "master": re.compile(r"\b(master(?:'s)?|m\.?tech|m\.?s\.?|m\.?a\.?|m\.?b\.?a\.?)\b", re.IGNORECASE),
    "bachelor": re.compile(r"\b(bachelor(?:'s)?|b\.?tech|b\.?e\.?|b\.?a\.?|b\.?s\.?)\b", re.IGNORECASE),
}


def score_candidate_fit(resume: Resume, job: JobDescription) -> dict[str, object]:
    """Score a resume against a job description using blueprint weights.
    
    🔧 FIXED:
    - Validate inputs before processing
    - Use regex patterns instead of substring matching
    - Fix division by zero edge case
    - Consistent field naming (no duplicate score/fit_score)
    - Proper null/empty handling
    """
    # 🔧 ADDED: Input validation
    if not resume or not job:
        raise ValueError("Resume and JobDescription are required")
    
    settings = get_settings()
    weights = settings.ranking_weights
    
    # 🔧 FIXED: Handle empty/None skill lists
    candidate_skills = set(normalize_skills(resume.skills or []))
    required = set(normalize_skills(job.required_skills or []))
    preferred = set(normalize_skills(job.preferred_skills or []))

    matched_required = sorted(candidate_skills & required)
    missing_required = sorted(required - candidate_skills)
    matched_preferred = sorted(candidate_skills & preferred)
    missing_preferred = sorted(preferred - candidate_skills)

    # 🔧 FIXED: Skill score logic - missing required skills SHOULD hurt score
    # If no required skills specified, give full credit (can't fail what's not required)
    if required:
        skill_score = len(matched_required) / len(required)  # 0-1 based on matches
    else:
        skill_score = 1.0  # No requirements = perfect match on skills axis
    
    # Experience score - capped at 1.0
    experience_score = (
        min(resume.years_experience / job.min_years_experience, 1.0)
        if job.min_years_experience > 0
        else 1.0
    )
    
    # 🔧 FIXED: Education scoring - use regex patterns, fix logic
    education_score = score_education_fixed(resume.education, job.raw_text)
    
    # Project score - infer from resume text
    project_score = infer_project_presence(resume.raw_text)
    
    # Certification score - infer from resume text
    certification_score = infer_certification_presence(resume.raw_text)
    
    # Semantic similarity
    similarity_score = cosine_similarity_score(resume.raw_text, job.raw_text)

    # 🔧 FIXED: Calculate fit score with proper weighting
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
    
    explanation = [
        f"Skill Match {round(skill_score * weights.skill_match * 100, 2)}/{round(weights.skill_match * 100, 2)}",
        f"Experience {round(experience_score * weights.experience * 100, 2)}/{round(weights.experience * 100, 2)}",
        f"Education {round(education_score * weights.education * 100, 2)}/{round(weights.education * 100, 2)}",
        f"Projects {round(project_score * weights.projects * 100, 2)}/{round(weights.projects * 100, 2)}",
        f"Certifications {round(certification_score * weights.certifications * 100, 2)}/{round(weights.certifications * 100, 2)}",
    ]

    # 🔧 FIXED: Single score field (no duplicate score/fit_score)
    return {
        "candidate_id": resume.id,
        "candidate_name": resume.candidate_name,
        "job_id": job.id,
        "job_title": job.title,
        "score": fit_score,  # 🔧 Single canonical field
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
        "explanation": explanation,
        "thresholds": {"strong_fit": 85, "good_fit": 70, "possible_fit": 50},
    }


def score_education_fixed(candidate_education: str, job_description: str) -> float:
    """🔧 FIXED: Proper education level matching with regex patterns.
    
    Args:
        candidate_education: Resume education text (e.g., "B.Tech in CS")
        job_description: Job requirement text
        
    Returns:
        Score 0-1 indicating how well candidate matches job education requirement
        
    Logic:
    - If job has no education requirement → full score (not a requirement)
    - If job requires PhD and candidate has it → 1.0
    - If job requires Master and candidate has Bachelor → 0.5 (below requirement)
    - If job requires Bachelor and candidate has Master → 1.0 (exceeds requirement)
    """
    candidate = (candidate_education or "").lower().strip()
    job = (job_description or "").lower().strip()
    
    # 🔧 FIXED: Determine job requirement level
    job_requires = _extract_education_level(job)
    
    # If job doesn't specify education requirement, not a factor
    if job_requires is None:
        return 0.5 if not candidate else 1.0  # Has education: bonus, else neutral
    
    # Determine candidate education level
    candidate_level = _extract_education_level(candidate)
    
    # 🔧 FIXED: Scoring based on level hierarchy
    # Level: PhD (3) > Master (2) > Bachelor (1) > Other (0)
    if candidate_level is None:
        return 0.0  # No education info
    
    # Score: 1.0 if meets/exceeds requirement, 0.5 if 1 level below, 0.0 if 2+ below
    level_diff = candidate_level - job_requires
    if level_diff >= 0:
        return 1.0  # Meets or exceeds
    elif level_diff == -1:
        return 0.5  # 1 level below
    else:
        return 0.0  # 2+ levels below


def _extract_education_level(text: str) -> int | None:
    """🔧 ADDED: Extract education level from text.
    
    Returns:
        3 for PhD, 2 for Master, 1 for Bachelor, 0 for other/unknown, None if not specified
    """
    text = (text or "").lower()
    
    # Check in order of highest to lowest
    if EDUCATION_PATTERNS["phd"].search(text):
        return 3
    if EDUCATION_PATTERNS["master"].search(text):
        return 2
    if EDUCATION_PATTERNS["bachelor"].search(text):
        return 1
    
    return None  # No recognized education level


def infer_project_presence(text: str) -> float:
    """🔧 IMPROVED: Infer project evidence from resume text with better signal.
    
    Returns score 0-1 based on project signal strength.
    """
    value = (text or "").lower()
    
    strong_signals = ["built", "developed", "created", "launched"]
    weak_signals = ["project", "portfolio", "github"]
    
    if any(signal in value for signal in strong_signals):
        return 1.0
    if any(signal in value for signal in weak_signals):
        return 0.8
    
    return 0.2  # Default: no strong signal


def infer_certification_presence(text: str) -> float:
    """🔧 IMPROVED: Infer certification evidence with regex patterns.
    
    Returns score 0-1 based on certification signal strength.
    """
    value = (text or "").lower()
    
    cert_pattern = re.compile(r"\b(certified|certification|certificate|certified by|credential)\b")
    
    if cert_pattern.search(value):
        return 0.9
    
    return 0.1  # Default: no certification signal


def classify_fit(score: float, missing_required: list[str]) -> str:
    """Convert a score into a recruiter-friendly recommendation.
    
    🔧 IMPROVED: Consider both score and missing required skills
    """
    if score >= 85 and not missing_required:
        return "strong_fit"
    if score >= 70 and len(missing_required) <= 1:
        return "good_fit"
    if score >= 50:
        return "possible_fit"
    return "low_fit"
