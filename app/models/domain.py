"""Internal domain models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass
class Resume:
    """Stored resume and extracted candidate profile.

    The fields map to the blueprint's Candidates table:
    id, name, email, experience, education, resume_path, created_at.
    """

    id: str
    name: str
    email: Optional[str]
    raw_text: str
    skills: list[str]
    experience: float
    education: str
    projects: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    resume_path: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)

    @property
    def candidate_name(self) -> str:
        """Backward-compatible alias used by older API responses."""
        return self.name

    @property
    def years_experience(self) -> float:
        """Backward-compatible alias used by older scoring responses."""
        return self.experience


@dataclass
class JobDescription:
    """Stored job description and extracted requirements."""

    id: str
    title: str
    description: str
    skills: list[str]
    experience: float
    preferred: list[str] = field(default_factory=list)
    max_experience: float = 0.0
    created_at: datetime = field(default_factory=utc_now)

    @property
    def raw_text(self) -> str:
        """Backward-compatible alias."""
        return self.description

    @property
    def required_skills(self) -> list[str]:
        """Blueprint jobs expose one normalized skill list."""
        return self.skills

    @property
    def preferred_skills(self) -> list[str]:
        """Preferred skills extracted or supplied from the job description."""
        return self.preferred

    @property
    def min_years_experience(self) -> float:
        """Backward-compatible alias."""
        return self.experience

    @property
    def max_years_experience(self) -> float:
        """Upper bound from JD ranges when available."""
        return self.max_experience or self.experience
