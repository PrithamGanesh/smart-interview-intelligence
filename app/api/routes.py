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


@router.post("/resume/upload", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED, tags=["resume"])
async def upload_resume(file: UploadFile = File(...)) -> object:
    """Blueprint endpoint: accept resume.pdf and parse candidate fields."""
    content = await file.read()
    return resume_service.create_resume_from_upload(content, file.filename or "resume.pdf")


@router.get("/resumes", response_model=list[ResumeResponse], tags=["resumes"])
def list_resumes() -> object:
    """List submitted resumes."""
    return resume_service.list_resumes()


@router.get("/candidates", response_model=list[ResumeResponse], tags=["candidates"])
def list_candidates() -> object:
    """Review endpoint: list/search candidate profiles."""
    return resume_service.list_resumes()


@router.get("/resumes/{resume_id}", response_model=ResumeResponse, tags=["resumes"])
def get_resume(resume_id: str) -> object:
    """Get one submitted resume profile."""
    return resume_service.get_resume(resume_id)


@router.get("/resume/{resume_id}", response_model=ResumeResponse, tags=["resume"])
def get_resume_blueprint(resume_id: str) -> object:
    """Blueprint endpoint: get one candidate by id."""
    return resume_service.get_resume(resume_id)


@router.delete("/resume/{resume_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["resume"])
def delete_resume_blueprint(resume_id: str) -> Response:
    """Review endpoint: delete a resume for right-to-erasure workflows."""
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


@router.get("/jobs", response_model=list[JobDescriptionResponse], tags=["jobs"])
def list_jobs() -> object:
    """List submitted job descriptions."""
    return job_service.list_jobs()


@router.get("/jobs/{job_id}", response_model=JobDescriptionResponse, tags=["jobs"])
def get_job(job_id: str) -> object:
    """Get one submitted job description profile."""
    return job_service.get_job(job_id)


@router.get("/job/{job_id}", response_model=JobDescriptionResponse, tags=["job"])
def get_job_blueprint(job_id: str) -> object:
    """Blueprint endpoint: get one job description by id."""
    return job_service.get_job(job_id)


@router.post("/extract", response_model=ExtractionResponse, tags=["analysis"])
def extract_profile(payload: ExtractionRequest) -> object:
    """Extract skills, experience, and keywords from arbitrary text."""
    return analysis_service.extract_profile(payload.text)


@router.get("/jobs/{job_id}/rankings", response_model=CandidateRankingResponse, tags=["analysis"])
def rank_candidates(job_id: str) -> object:
    """Rank all candidates for a job."""
    return analysis_service.rank_candidates(job_id)


@router.post("/match", response_model=MatchResponse, tags=["matching"])
def match_candidate(payload: MatchRequest) -> object:
    """Blueprint endpoint: embedding-based candidate/job match."""
    return analysis_service.match(payload.candidate_id, payload.job_id)


@router.post("/rank", response_model=RankResponse, tags=["ranking"])
def rank_candidates_blueprint(payload: RankRequest) -> object:
    """Blueprint endpoint: rank candidates using configured weights."""
    return analysis_service.rank_candidates_blueprint(payload.job_id, payload.candidate_ids)


@router.get("/jobs/{job_id}/candidates/{candidate_id}/fit", response_model=FitPredictionResponse, tags=["analysis"])
def predict_fit(job_id: str, candidate_id: str) -> object:
    """Predict candidate-job fit."""
    return analysis_service.predict_fit(candidate_id, job_id)


@router.get("/jobs/{job_id}/candidates/{candidate_id}/skill-gaps", response_model=SkillGapResponse, tags=["analysis"])
def identify_skill_gaps(job_id: str, candidate_id: str) -> object:
    """Identify candidate skill and experience gaps for a job."""
    return analysis_service.identify_skill_gaps(candidate_id, job_id)


@router.get("/candidates/{candidate_id}/gap", response_model=SkillGapResponse, tags=["candidates"])
def identify_candidate_gap(candidate_id: str, job_id: str = Query(...)) -> object:
    """Review endpoint: identify gaps for a candidate against a selected job."""
    return analysis_service.identify_skill_gaps(candidate_id, job_id)


@router.post("/interview-questions", response_model=InterviewQuestionResponse, tags=["analysis"])
def generate_interview_questions(payload: InterviewQuestionRequest) -> object:
    """Generate role-specific interview questions."""
    return analysis_service.generate_interview_questions(
        candidate_id=payload.candidate_id,
        job_id=payload.job_id,
        count=payload.count,
        skills=payload.skills,
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


@router.get("/questions/{job_id}", response_model=InterviewQuestionResponse, tags=["questions"])
def get_cached_questions(job_id: str, candidate_id: str = Query(default="")) -> object:
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


@router.get("/dashboard", response_model=DashboardResponse, tags=["dashboard"])
def recruiter_dashboard(job_id: Optional[str] = Query(default=None)) -> object:
    """Provide recruiter dashboard metrics."""
    return analysis_service.recruiter_dashboard(job_id=job_id)
