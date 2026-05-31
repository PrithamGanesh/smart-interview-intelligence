"""Application configuration."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional
from pydantic import BaseModel, Field


class RankingWeights(BaseModel):
    """Blueprint ranking weights."""

    skill_match: float = 0.40
    experience: float = 0.25
    education: float = 0.10
    projects: float = 0.15
    certifications: float = 0.10


class Settings(BaseModel):
    """Runtime settings for the API service."""

    project_name: str = "Smart Interview Intelligence"
    version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])
    api_key: Optional[str] = None
    database_url: str = "postgresql+psycopg2://postgres:postgres@postgres:5432/smart_interview"
    redis_url: str = "redis://redis:6379/0"
    embedding_model_name: str = "all-MiniLM-L6-v2"
    success_model_name: str = "XGBoostClassifier"
    ranking_weights: RankingWeights = Field(default_factory=RankingWeights)
    max_generated_questions: int = 12
    default_question_count: int = 6
    max_resume_upload_bytes: int = 5 * 1024 * 1024
    allowed_resume_extensions: list[str] = Field(default_factory=lambda: [".pdf", ".txt", ".docx"])
    rate_limit_per_minute: int = 120


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings(
        project_name=os.getenv("PROJECT_NAME", "Smart Interview Intelligence"),
        version=os.getenv("APP_VERSION", "0.1.0"),
        api_prefix=os.getenv("API_PREFIX", "/api/v1"),
        api_key=os.getenv("API_KEY") or None,
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://postgres:postgres@postgres:5432/smart_interview",
        ),
        redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
        embedding_model_name=os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"),
        max_resume_upload_bytes=int(os.getenv("MAX_RESUME_UPLOAD_BYTES", str(5 * 1024 * 1024))),
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "120")),
    )
