"""SQLAlchemy database models matching the blueprint schema."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


def utc_now() -> datetime:
    """Return timezone-aware UTC time for persisted rows."""
    return datetime.now(timezone.utc)


class Candidate(Base):
    """Candidates table."""

    __tablename__ = "candidates"

    id = Column(String(64), primary_key=True)
    name = Column(String(160), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    experience = Column(Float, default=0.0, nullable=False)
    education = Column(String(255), default="", nullable=False)
    resume_path = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    skills = relationship("CandidateSkill", back_populates="candidate", cascade="all, delete-orphan")


class Skill(Base):
    """Skills table."""

    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False, unique=True, index=True)

    candidates = relationship("CandidateSkill", back_populates="skill", cascade="all, delete-orphan")


class CandidateSkill(Base):
    """CandidateSkills association table."""

    __tablename__ = "candidate_skills"
    __table_args__ = (UniqueConstraint("candidate_id", "skill_id", name="uq_candidate_skill"),)

    candidate_id = Column(String(64), ForeignKey("candidates.id"), primary_key=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), primary_key=True)

    candidate = relationship("Candidate", back_populates="skills")
    skill = relationship("Skill", back_populates="candidates")


class Job(Base):
    """Jobs table."""

    __tablename__ = "jobs"

    id = Column(String(64), primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)


class MatchResult(Base):
    """MatchResults table."""

    __tablename__ = "match_results"
    __table_args__ = (UniqueConstraint("candidate_id", "job_id", name="uq_candidate_job_match"),)

    candidate_id = Column(String(64), ForeignKey("candidates.id"), primary_key=True)
    job_id = Column(String(64), ForeignKey("jobs.id"), primary_key=True)
    score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=True)
