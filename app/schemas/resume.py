"""Resume API schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ResumeCreate(BaseModel):
    """Payload for submitting a resume."""

    candidate_name: Optional[str] = Field(default=None, max_length=120)
    name: Optional[str] = Field(default=None, max_length=120)
    email: Optional[str] = None
    resume_text: str = Field(..., min_length=30)
    education: Optional[str] = None
    resume_path: Optional[str] = None


class ResumeResponse(BaseModel):
    """Stored resume response."""

    id: str
    name: str
    candidate_name: str
    email: Optional[str]
    skills: list[str]
    experience: float
    years_experience: float
    education: str
    projects: list[str]
    certifications: list[str]
    resume_path: Optional[str]
    created_at: datetime


class ResumeUploadResponse(BaseModel):
    """Blueprint resume parser output."""

    id: str
    name: str
    email: Optional[str]
    skills: list[str]
    experience: float
    education: str
    resume_path: Optional[str]
    created_at: datetime
