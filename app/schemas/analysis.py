"""Analysis API schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class ExtractionRequest(BaseModel):
    """Text extraction request."""

    text: str = Field(..., min_length=10)


class ExtractionResponse(BaseModel):
    """Skills and experience extraction response."""

    skills: list[str]
    years_experience: float
    keywords: list[str]


class MatchRequest(BaseModel):
    """Candidate-job matching request."""

    candidate_id: str
    job_id: str


class MatchResponse(BaseModel):
    """Blueprint matching response."""

    candidate_id: str
    job_id: str
    score: float
    match_score: float
    similarity_score: float


class FitPredictionResponse(BaseModel):
    """Candidate-job fit response."""

    candidate_id: str
    candidate_name: str
    job_id: str
    job_title: str
    fit_score: float
    recommendation: str
    matched_required_skills: list[str]
    missing_required_skills: list[str]
    matched_preferred_skills: list[str]
    missing_preferred_skills: list[str]
    experience_score: float
    candidate_years_experience: float
    required_years_experience: float
    score: float
    similarity_score: float
    skill_score: float
    education_score: float
    project_score: float
    certification_score: float
    explanation: list[str] = Field(default_factory=list)
    thresholds: dict[str, float] = Field(default_factory=dict)


class CandidateRankingResponse(BaseModel):
    """Ranked candidate response."""

    job_id: str
    job_title: str
    rankings: list[FitPredictionResponse]


class RankRequest(BaseModel):
    """Candidate ranking request."""

    job_id: str
    candidate_ids: list[str] = Field(default_factory=list)


class RankedCandidate(BaseModel):
    """Blueprint ranking item."""

    rank: int
    candidate_id: str
    name: str
    score: float
    feature_scores: dict[str, float]
    explanation: list[str] = Field(default_factory=list)


class RankResponse(BaseModel):
    """Blueprint ranking response."""

    job_id: str
    rankings: list[RankedCandidate]


class SkillGapResponse(BaseModel):
    """Skill gap analysis response."""

    candidate_id: str
    job_id: str
    missing_required_skills: list[str]
    missing_preferred_skills: list[str]
    missing_skills: list[str]
    experience_gap_years: float
    priority_gaps: list[str]
    gap_details: list[dict[str, str]] = Field(default_factory=list)


class InterviewQuestionRequest(BaseModel):
    """Question generation request."""

    candidate_id: str
    job_id: str
    skills: list[str] = Field(default_factory=list)
    count: int = Field(default=6, ge=1, le=12)


class InterviewQuestionResponse(BaseModel):
    """Generated interview questions."""

    candidate_id: str
    job_id: str
    questions: list[str]


class SuccessPredictionRequest(BaseModel):
    """Candidate success prediction request."""

    candidate_id: Optional[str] = None
    job_id: Optional[str] = None
    skill_score: Optional[float] = Field(default=None, ge=0, le=100)
    experience: Optional[float] = Field(default=None, ge=0)
    education: Optional[str] = None


class SuccessPredictionResponse(BaseModel):
    """Candidate success prediction response."""

    candidate_id: Optional[str]
    job_id: Optional[str]
    success_probability: float
    model: str
    model_version: str = "unversioned"
    feature_contributions: dict[str, float] = Field(default_factory=dict)


class DashboardResponse(BaseModel):
    """Recruiter dashboard summary."""

    total_candidates: int
    total_jobs: int
    average_fit_score: float
    recommendation_counts: dict[str, int]
    top_candidates: list[FitPredictionResponse]
    most_common_skills: list[str]
