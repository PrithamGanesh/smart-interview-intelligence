"""SQLAlchemy ORM models for PostgreSQL."""

import json
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    VARCHAR,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Resume(Base):
    """Resume/candidate record."""
    __tablename__ = "resumes"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    email: Mapped[Optional[str]] = mapped_column(VARCHAR(255))
    phone: Mapped[Optional[str]] = mapped_column(VARCHAR(20))
    raw_text: Mapped[str] = mapped_column(Text)
    parsed_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    embedding_vector: Mapped[Optional[list]] = mapped_column(JSON)  # Will use pgvector in future
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index("idx_resumes_tenant_id", "tenant_id"),
        Index("idx_resumes_email", "email"),
        Index("idx_resumes_created_at", "created_at"),
    )


class JobDescription(Base):
    """Job posting record."""
    __tablename__ = "jobs"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False)
    title: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills: Mapped[dict] = mapped_column(JSONB, default=dict)
    experience_years_min: Mapped[Optional[int]] = mapped_column(Integer)
    experience_years_max: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_jobs_tenant_id", "tenant_id"),
        Index("idx_jobs_title", "title"),
    )


class MatchResult(Base):
    """Cached match results between resume and job."""
    __tablename__ = "match_results"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    resume_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("resumes.id"), nullable=False)
    job_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("jobs.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    fit_score: Mapped[float] = mapped_column(Float, nullable=False)
    skill_match: Mapped[float] = mapped_column(Float, nullable=False)
    experience_match: Mapped[float] = mapped_column(Float, nullable=False)
    education_match: Mapped[float] = mapped_column(Float, nullable=False)
    projects_match: Mapped[float] = mapped_column(Float, nullable=False)
    certs_match: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ttl: Mapped[int] = mapped_column(Integer, default=3600)  # TTL in seconds
    
    __table_args__ = (
        UniqueConstraint("resume_id", "job_id", "tenant_id", name="uk_match_results_composite"),
        Index("idx_match_results_job_id", "job_id"),
        Index("idx_match_results_computed_at", "computed_at"),
    )


class InterviewQuestion(Base):
    """Generated and cached interview questions."""
    __tablename__ = "interview_questions"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("jobs.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(VARCHAR(20))
    topic: Mapped[str] = mapped_column(VARCHAR(100))
    question_hash: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)  # SHA256
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint("question_hash", "job_id", name="uk_questions_hash_job"),
        Index("idx_questions_job_id", "job_id"),
    )


class Tenant(Base):
    """Tenant/organization record for multi-tenancy."""
    __tablename__ = "tenants"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    api_key: Mapped[str] = mapped_column(VARCHAR(255), unique=True, nullable=False)
    rate_limit_per_sec: Mapped[int] = mapped_column(Integer, default=10000)
    max_resumes: Mapped[int] = mapped_column(Integer, default=100000)
    storage_quota_gb: Mapped[int] = mapped_column(Integer, default=1000)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_tenants_api_key", "api_key"),
    )


class AuditLog(Base):
    """Audit trail for all operations."""
    __tablename__ = "audit_log"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))
    action: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(VARCHAR(50))
    resource_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index("idx_audit_log_tenant_id", "tenant_id"),
        Index("idx_audit_log_timestamp", "timestamp"),
    )
