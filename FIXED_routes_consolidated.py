"""FIXED: Consolidated API routes with single canonical endpoints.

🔧 IMPROVEMENTS:
- Single endpoint per resource (no duplicates)
- Pagination support on all list endpoints
- Proper HTTP status codes
- Consistent response naming
- Uses /api/v1 prefix from config
- Added missing DELETE endpoint for jobs
"""

from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, File, Query, Response, UploadFile, status

from app.schemas.analysis import (
    CandidateRankingResponse,
    DashboardResponse,
    ExtractionRequest,
    ExtractionResponse,
    FitPredictionResponse,
    InterviewQuestionRequest,
    InterviewQuestionResponse,
    MatchRequest,
    MatchResponse,
    RankRequest,
    RankResponse,
    SkillGapResponse,
    SuccessPredictionRequest,
    SuccessPredictionResponse,
)
from app.schemas.job import JobDescriptionCreate, JobDescriptionResponse
from app.schemas.resume import ResumeCreate, ResumeResponse, ResumeUploadResponse
from app.services.analysis_service import analysis_service
from app.services.job_service import job_service
from app.services.resume_service import resume_service


router = APIRouter(prefix="/api/v1", tags=["v1"])


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health", tags=["health"], response_model=dict[str, str])
def health() -> dict[str, str]:
    """Versioned health check for load balancers."""
    return {"status": "healthy", "version": "1"}


# ============================================================================
# RESUME ENDPOINTS (Canonical: /resumes)
# ============================================================================

@router.post(
    "/resumes", 
    response_model=ResumeResponse, 
    status_code=status.HTTP_201_CREATED,
    tags=["resumes"],
    summary="Create resume from text"
)
def create_resume(payload: ResumeCreate) -> ResumeResponse:
    """Accept and analyze a resume from text or structured data."""
    return resume_service.create_resume(payload)


@router.post(
    "/resumes/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["resumes"],
    summary="Upload resume file"
)
async def upload_resume(file: UploadFile = File(...)) -> ResumeUploadResponse:
    """Accept resume.pdf/.docx/.txt file and parse candidate fields."""
    content = await file.read()
    return resume_service.create_resume_from_upload(content, file.filename or "resume.pdf")


@router.get(
    "/resumes",
    response_model=list[ResumeResponse],
    tags=["resumes"],
    summary="List all resumes"
)
def list_resumes(
    limit: int = Query(50, ge=1, le=200, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> list[ResumeResponse]:
    """List submitted resumes with pagination.
    
    🔧 ADDED: Pagination support to prevent memory exhaustion
    """
    resumes, total = resume_service.list_resumes(limit=limit, offset=offset)
    return resumes


@router.get(
    "/resumes/{resume_id}",
    response_model=ResumeResponse,
    tags=["resumes"],
    summary="Get resume by ID"
)
def get_resume(resume_id: str) -> ResumeResponse:
    """Get one submitted resume profile."""
    return resume_service.get_resume(resume_id)


@router.delete(
    "/resumes/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["resumes"],
    summary="Delete resume"
)
def delete_resume(resume_id: str) -> Response:
    """Delete a resume (GDPR/privacy compliance)."""
    resume_service.delete_resume(resume_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# JOB DESCRIPTION ENDPOINTS (Canonical: /jobs)
# ============================================================================

@router.post(
    "/jobs",
    response_model=JobDescriptionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["jobs"],
    summary="Create job description"
)
def create_job(payload: JobDescriptionCreate) -> JobDescriptionResponse:
    """Accept and analyze a job description."""
    return job_service.create_job(payload)


@router.get(
    "/jobs",
    response_model=list[JobDescriptionResponse],
    tags=["jobs"],
    summary="List all jobs"
)
def list_jobs(
    limit: int = Query(50, ge=1, le=200, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> list[JobDescriptionResponse]:
    """List submitted job descriptions with pagination.
    
    🔧 ADDED: Pagination support
    """
    jobs, total = job_service.list_jobs(limit=limit, offset=offset)
    return jobs


@router.get(
    "/jobs/{job_id}",
    response_model=JobDescriptionResponse,
    tags=["jobs"],
    summary="Get job by ID"
)
def get_job(job_id: str) -> JobDescriptionResponse:
    """Get one job description profile."""
    return job_service.get_job(job_id)


@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["jobs"],
    summary="Delete job"
)
def delete_job(job_id: str) -> Response:
    """🔧 ADDED: Delete a job description."""
    job_service.delete_job(job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# ANALYSIS ENDPOINTS
# ============================================================================

@router.post(
    "/extract",
    response_model=ExtractionResponse,
    tags=["analysis"],
    summary="Extract profile from text"
)
def extract_profile(payload: ExtractionRequest) -> ExtractionResponse:
    """Extract skills, experience, and keywords from arbitrary text."""
    return analysis_service.extract_profile(payload.text)


@router.get(
    "/jobs/{job_id}/rankings",
    response_model=CandidateRankingResponse,
    tags=["analysis"],
    summary="Rank candidates for a job"
)
def rank_candidates(
    job_id: str,
    limit: int = Query(50, ge=1, le=200, description="Max rankings to return"),
) -> CandidateRankingResponse:
    """Rank candidates for a job with pagination.
    
    🔧 ADDED: Pagination to prevent computing 1M+ matches
    """
    return analysis_service.rank_candidates(job_id, limit=limit)


@router.post(
    "/match",
    response_model=MatchResponse,
    tags=["matching"],
    summary="Match candidate to job"
)
def match_candidate(payload: MatchRequest) -> MatchResponse:
    """Embedding-based candidate/job match score."""
    return analysis_service.match(payload.candidate_id, payload.job_id)


@router.post(
    "/rank",
    response_model=RankResponse,
    tags=["ranking"],
    summary="Rank specific candidates"
)
def rank_candidates_blueprint(
    payload: RankRequest,
    limit: int = Query(100, ge=1, le=500, description="Max rankings"),
) -> RankResponse:
    """Rank specific candidates for a job."""
    return analysis_service.rank_candidates_blueprint(
        payload.job_id, 
        payload.candidate_ids,
        limit=limit
    )


@router.get(
    "/jobs/{job_id}/candidates/{candidate_id}/fit",
    response_model=FitPredictionResponse,
    tags=["analysis"],
    summary="Predict candidate-job fit"
)
def predict_fit(job_id: str, candidate_id: str) -> FitPredictionResponse:
    """Predict candidate-job fit with scoring breakdown."""
    return analysis_service.predict_fit(candidate_id, job_id)


@router.get(
    "/jobs/{job_id}/candidates/{candidate_id}/skill-gaps",
    response_model=SkillGapResponse,
    tags=["analysis"],
    summary="Identify skill gaps"
)
def identify_skill_gaps(job_id: str, candidate_id: str) -> SkillGapResponse:
    """Identify candidate skill and experience gaps for a job."""
    return analysis_service.identify_skill_gaps(candidate_id, job_id)


@router.post(
    "/jobs/{job_id}/candidates/{candidate_id}/questions",
    response_model=InterviewQuestionResponse,
    tags=["analysis"],
    summary="Generate interview questions"
)
def generate_interview_questions(
    job_id: str,
    candidate_id: str,
    count: int = Query(6, ge=1, le=12, description="Number of questions"),
) -> InterviewQuestionResponse:
    """Generate interview questions for a candidate-job pair."""
    return analysis_service.generate_interview_questions(
        candidate_id=candidate_id,
        job_id=job_id,
        count=count,
    )


@router.get(
    "/jobs/{job_id}/questions",
    response_model=list[str],
    tags=["analysis"],
    summary="Get cached questions"
)
def get_cached_questions(job_id: str) -> list[str]:
    """Get previously generated questions for a job."""
    result = analysis_service.get_cached_questions(job_id)
    return result.get("questions", [])


@router.post(
    "/success-prediction",
    response_model=SuccessPredictionResponse,
    tags=["analysis"],
    summary="Predict success probability"
)
def predict_success(payload: SuccessPredictionRequest) -> SuccessPredictionResponse:
    """Predict candidate success probability for a role."""
    return analysis_service.predict_success(
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        skill_score=payload.skill_score,
        experience=payload.experience,
        education=payload.education,
    )


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    tags=["analysis"],
    summary="Get recruiter dashboard"
)
def recruiter_dashboard(
    job_id: Optional[str] = Query(None, description="Filter by job (optional)"),
    limit: int = Query(5, ge=1, le=10, description="Top N candidates to show"),
) -> DashboardResponse:
    """Get recruiter dashboard with summary statistics.
    
    🔧 ADDED: Pagination support in dashboard
    """
    return analysis_service.recruiter_dashboard(job_id=job_id, limit_top=limit)
