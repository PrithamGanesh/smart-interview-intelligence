"""Resume parsing service.

Supports PDF parsing through pdfplumber/PyMuPDF when installed, and plain text
fallbacks for local development and tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.utils.text import (
    extract_candidate_name,
    extract_education,
    extract_email,
    extract_section_items,
    extract_skills,
    extract_years_experience,
    normalize_text,
)


def extract_text_from_bytes(content: bytes, filename: str = "resume.txt") -> str:
    """Extract text from uploaded resume bytes."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_text(content)
    return content.decode("utf-8", errors="ignore")


def parse_resume_text(text: str, candidate_name: Optional[str] = None, resume_path: Optional[str] = None) -> dict[str, object]:
    """Parse normalized candidate profile fields from resume text."""
    cleaned = normalize_text(text)
    return {
        "name": candidate_name or extract_candidate_name(text),
        "email": extract_email(text),
        "skills": extract_skills(text),
        "experience": extract_years_experience(text),
        "education": extract_education(text),
        "projects": extract_section_items(text, ("projects",)),
        "certifications": extract_section_items(text, ("certifications", "certificates")),
        "resume_path": resume_path,
        "raw_text": cleaned,
    }


def _extract_pdf_text(content: bytes) -> str:
    """Extract PDF text with pdfplumber first, then PyMuPDF."""
    try:
        import io
        import pdfplumber

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception:
        pass

    try:
        import fitz

        with fitz.open(stream=content, filetype="pdf") as document:
            return "\n".join(page.get_text() for page in document)
    except Exception as exc:
        raise ValueError("Unable to parse PDF. Install pdfplumber or PyMuPDF, or upload text content.") from exc
