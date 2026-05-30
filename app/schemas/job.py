"""Job description API schemas."""

from __future__ import annotations

from typing import Optional

from datetime import datetime
from pydantic import BaseModel, Field


class JobDescriptionCreate(BaseModel):
    """Payload for submitting a job description."""

    title: str = Field(..., min_length=1, max_length=160)
    description: str = Field(..., min_length=30)
    skills: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience: Optional[float] = Field(default=None, ge=0)
    min_years_experience: Optional[float] = Field(default=None, ge=0)


class JobDescriptionResponse(BaseModel):
    """Stored job description response."""

    id: str
    title: str
    description: str
    skills: list[str]
    experience: float
    required_skills: list[str]
    preferred_skills: list[str]
    min_years_experience: float
    created_at: datetime
