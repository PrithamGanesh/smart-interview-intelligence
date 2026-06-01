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

    # Application
    PROJECT_NAME: str = "Smart Interview Intelligence"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Security
    ALLOWED_ORIGINS: list[str] = Field(default_factory=lambda: ["*"])
    API_KEY: Optional[str] = None
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/smart_interview"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False
    
    # Cache
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 3600
    CACHE_TTL_MATCH_RESULTS: int = 21600  # 6 hours
    CACHE_TTL_EMBEDDINGS: int = 604800    # 7 days
    
    # ML Models
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    SUCCESS_MODEL_PATH: str = "app/ml/models/success_predictor.pkl"
    
    # API Configuration
    MAX_RESUME_UPLOAD_BYTES: int = 5 * 1024 * 1024
    ALLOWED_RESUME_EXTENSIONS: list[str] = Field(default_factory=lambda: [".pdf", ".txt", ".docx"])
    MAX_GENERATED_QUESTIONS: int = 12
    DEFAULT_QUESTION_COUNT: int = 6
    PAGE_SIZE_DEFAULT: int = 20
    PAGE_SIZE_MAX: int = 100
    
    # Rate Limiting
    RATE_LIMIT_PER_SEC: int = 10000
    RATE_LIMIT_BURST: int = 100
    
    # Ranking & Scoring
    RANKING_WEIGHTS: RankingWeights = Field(default_factory=RankingWeights)
    
    # Async Workers
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    WORKER_CONCURRENCY: int = 4
    
    class Config:
        env_file = ".env"
        case_sensitive = True


def _get_settings() -> Settings:
    """Create settings from environment variables."""
    return Settings(
        PROJECT_NAME=os.getenv("PROJECT_NAME", "Smart Interview Intelligence"),
        VERSION=os.getenv("VERSION", "1.0.0"),
        API_PREFIX=os.getenv("API_PREFIX", "/api/v1"),
        DEBUG=os.getenv("DEBUG", "false").lower() == "true",
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
        
        ALLOWED_ORIGINS=os.getenv("ALLOWED_ORIGINS", "*").split(","),
        API_KEY=os.getenv("API_KEY"),
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY"),
        JWT_ALGORITHM=os.getenv("JWT_ALGORITHM", "HS256"),
        
        DATABASE_URL=os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/smart_interview"),
        DB_POOL_SIZE=int(os.getenv("DB_POOL_SIZE", "20")),
        DB_MAX_OVERFLOW=int(os.getenv("DB_MAX_OVERFLOW", "10")),
        DB_ECHO=os.getenv("DB_ECHO", "false").lower() == "true",
        
        REDIS_URL=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        CACHE_TTL_SECONDS=int(os.getenv("CACHE_TTL_SECONDS", "3600")),
        CACHE_TTL_MATCH_RESULTS=int(os.getenv("CACHE_TTL_MATCH_RESULTS", "21600")),
        CACHE_TTL_EMBEDDINGS=int(os.getenv("CACHE_TTL_EMBEDDINGS", "604800")),
        
        EMBEDDING_MODEL_NAME=os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"),
        SUCCESS_MODEL_PATH=os.getenv("SUCCESS_MODEL_PATH", "app/ml/models/success_predictor.pkl"),
        
        MAX_RESUME_UPLOAD_BYTES=int(os.getenv("MAX_RESUME_UPLOAD_BYTES", str(5 * 1024 * 1024))),
        MAX_GENERATED_QUESTIONS=int(os.getenv("MAX_GENERATED_QUESTIONS", "12")),
        DEFAULT_QUESTION_COUNT=int(os.getenv("DEFAULT_QUESTION_COUNT", "6")),
        PAGE_SIZE_DEFAULT=int(os.getenv("PAGE_SIZE_DEFAULT", "20")),
        PAGE_SIZE_MAX=int(os.getenv("PAGE_SIZE_MAX", "100")),
        
        RATE_LIMIT_PER_SEC=int(os.getenv("RATE_LIMIT_PER_SEC", "10000")),
        RATE_LIMIT_BURST=int(os.getenv("RATE_LIMIT_BURST", "100")),
        
        CELERY_BROKER_URL=os.getenv("CELERY_BROKER_URL"),
        CELERY_RESULT_BACKEND=os.getenv("CELERY_RESULT_BACKEND"),
        WORKER_CONCURRENCY=int(os.getenv("WORKER_CONCURRENCY", "4")),
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return _get_settings()
