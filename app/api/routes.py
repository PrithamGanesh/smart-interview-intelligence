"""HTTP routes for Smart Interview Intelligence."""

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
from app.utils.taxonomy import load_skill_taxonomy


router = APIRouter()


@router.get("/health", tags=["health"])
def health() -> dict[str, str]:
    """Versioned health check for load balancers."""
    return {"status": "healthy"}


@router.post("/resumes", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED, tags=["resumes"])
def create_resume(payload: ResumeCreate) -> object:
    """Accept and analyze a resume."""
    return resume_service.create_resume(payload)


@router.post("/resumes/upload", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED, tags=["resumes"], summary="Upload resume file")
async def upload_resume(file: UploadFile = File(...)) -> ResumeUploadResponse:
    """🔧 FIXED: Accept resume.pdf/.docx/.txt file and parse candidate fields."""
    content = await file.read()
    return resume_service.create_resume_from_upload(content, file.filename or "resume.pdf")


@router.get("/resumes", response_model=list[ResumeResponse], tags=["resumes"], summary="List all resumes")
def list_resumes(
    limit: int = Query(50, ge=1, le=200, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> list[ResumeResponse]:
    """🔧 FIXED: List submitted resumes with pagination support to prevent memory exhaustion."""
    resumes, total = resume_service.list_resumes(limit=limit, offset=offset)
    return resumes


@router.get("/resumes/{resume_id}", response_model=ResumeResponse, tags=["resumes"], summary="Get resume by ID")
def get_resume(resume_id: str) -> ResumeResponse:
    """Get one submitted resume profile."""
    return resume_service.get_resume(resume_id)


@router.delete("/resumes/{resume_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["resumes"], summary="Delete resume")
def delete_resume(resume_id: str) -> Response:
    """🔧 FIXED: Delete a resume (GDPR/privacy compliance)."""
    resume_service.delete_resume(resume_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/jobs", response_model=JobDescriptionResponse, status_code=status.HTTP_201_CREATED, tags=["jobs"])
def create_job(payload: JobDescriptionCreate) -> object:
    """Accept and analyze a job description."""
    return job_service.create_job(payload)


@router.post("/job/create", response_model=JobDescriptionResponse, status_code=status.HTTP_201_CREATED, tags=["job"])
def create_job_blueprint(payload: JobDescriptionCreate) -> object:
    """Blueprint endpoint: create and analyze a job description."""
    return job_service.create_job(payload)


@router.get("/jobs", response_model=list[JobDescriptionResponse], tags=["jobs"], summary="List all jobs")
def list_jobs(
    limit: int = Query(50, ge=1, le=200, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> list[JobDescriptionResponse]:
    """🔧 FIXED: List submitted job descriptions with pagination support."""
    jobs, total = job_service.list_jobs(limit=limit, offset=offset)
    return jobs


@router.get("/jobs/{job_id}", response_model=JobDescriptionResponse, tags=["jobs"], summary="Get job by ID")
def get_job(job_id: str) -> JobDescriptionResponse:
    """Get one job description profile."""
    return job_service.get_job(job_id)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["jobs"], summary="Delete job")
def delete_job(job_id: str) -> Response:
    """🔧 ADDED: Delete a job description."""
    job_service.delete_job(job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENTrofile(payload.text)


@router.get("/jobs/{job_id}/rankings", response_model=CandidateRankingResponse, tags=["analysis"])
def rank_candidates(job_id: str) -> object:, summary="Rank candidates for a job")
def rank_candidates(
    job_id: str,
    limit: int = Query(50, ge=1, le=200, description="Max rankings to return"),
) -> CandidateRankingResponse:
    """🔧 FIXED: Rank candidates for a job with pagination to prevent O(N*M) computation."""
    return analysis_service.rank_candidates(job_id, limit=limit

@router.post("/match", response_model=MatchResponse, tags=["matching"])
def match_candidate(payload: MatchRequest) -> object:
    """Blueprint endpoint: embedding-based candidate/job match."""
    return analysis_service.match(payload.candidate_id, payload.job_id)
, summary="Rank specific candidates")
def rank_candidates_blueprint(
    payload: RankRequest,
    limit: int = Query(100, ge=1, le=500, description="Max rankings"),
) -> RankResponse:
    """Rank specific candidates for a job."""
    return analysis_service.rank_candidates_blueprint(
        payload.job_id, 
        payload.candidate_ids,
        limit=limit
    
    """Blueprint endpoint: rank candidates using configured weights."""
    return analysis_service.rank_candidates_blueprint(payload.job_id, payload.candidate_ids)


@router.get("/jobs/{job_id}/candidates/{candidate_id}/fit", response_model=FitPredictionResponse, tags=["analysis"])
def predict_fit(job_id: str, candidate_id: str) -> object:
    """Predict candidate-job fit."""
    return analysis_service.predict_fit(candidate_id, job_id)


@router.get("/jobs/{job_id}/candidates/{candidate_id}/skill-gaps", response_model=SkillGapResponse, tags=["analysis"])
def identify_skill_gaps(job_id: str, candidate_id: str) -> object:
    """Identify candidate skill and experience gaps for a job.""", summary="Generate interview questions")
def generate_interview_questions(
    payload: InterviewQuestionRequest,
    count: int = Query(6, ge=1, le=12, description="Number of questions"),
) -> InterviewQuestionResponse:
    """🔧 FIXED: Generate interview questions for a candidate-job pair."""
    return analysis_service.generate_interview_questions(
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        count=.skills,
    )


@router.post("/questions", response_model=InterviewQuestionResponse, tags=["questions"])
def generate_questions_blueprint(payload: InterviewQuestionRequest) -> object:
    """Blueprint endpoint: generate skill-template interview questions."""
    return analysis_service.generate_interview_questions(
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        count=payload.count,
        skills=payload.skills,
    )
jobs/{job_id}/questions", response_model=list[str], tags=["analysis"], summary="Get cached questions")
def get_cached_questions(job_id: str) -> list[str]:
    """Get previously generated questions for a job."""
    result = analysis_service.get_cached_questions(job_id)
    return result.get("questions", []
    """Review endpoint: retrieve cached/generated question bank entries."""
    return analysis_service.get_cached_questions(job_id=job_id, candidate_id=candidate_id)


@router.get("/taxonomy/skills", tags=["taxonomy"])
def list_skill_taxonomy() -> dict[str, object]:
    """Review endpoint: expose the active skill taxonomy."""
    taxonomy = load_skill_taxonomy()
    return {"count": len(taxonomy), "skills": taxonomy}


@router.post("/predict-success", response_model=SuccessPredictionResponse, tags=["prediction"])
def predict_success(payload: SuccessPredictionRequest) -> object:
    """Blueprint endpoint: predict candidate success probability."""
    return analysis_service.predict_success(
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        skill_score=payload.skill_score,
        experience=payload.experience,
        education=payload.education,
    )


@router.get("/dashboard", response_model=DashboardResponse, tags=["dashboard"], summary="Get recruiter dashboard")
def recruiter_dashboard(
    job_id: str = Query(None, description="Filter by job (optional)"),
    limit: int = Query(5, ge=1, le=10, description="Top N candidates to show"),
) -> DashboardResponse:
    """🔧 FIXED: Get recruiter dashboard with summary statistics and pagination."""
    return analysis_service.recruiter_dashboard(job_id=job_id, limit_top=limit)
