"""Resume parsing service.

Supports PDF parsing through pdfplumber/PyMuPDF when installed, and plain text
fallbacks for local development and tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.utils.privacy import mask_pii
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
    validate_resume_upload(content, filename)
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_text(content)
    if suffix == ".docx":
        return _extract_docx_text(content)
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
        "raw_text": mask_pii(cleaned),
    }


def validate_resume_upload(content: bytes, filename: str) -> None:
    """Reject unsafe or unsupported resume uploads before parsing."""
    settings = get_settings()
    suffix = Path(filename or "").suffix.lower()
    if suffix not in settings.allowed_resume_extensions:
        allowed = ", ".join(settings.allowed_resume_extensions)
        raise ValidationError(f"Unsupported resume file type '{suffix or 'unknown'}'. Allowed types: {allowed}.")
    if not content:
        raise ValidationError("Resume upload is empty.")
    if len(content) > settings.max_resume_upload_bytes:
        limit_mb = settings.max_resume_upload_bytes / (1024 * 1024)
        raise ValidationError(f"Resume upload exceeds the {limit_mb:g} MB size limit.")


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


def _extract_docx_text(content: bytes) -> str:
    """Extract text from a DOCX file when python-docx is installed."""
    try:
        import io
        from docx import Document

        document = Document(io.BytesIO(content))
        paragraphs = [paragraph.text for paragraph in document.paragraphs]
        return "\n".join(paragraph for paragraph in paragraphs if paragraph.strip())
    except Exception as exc:
        raise ValueError("Unable to parse DOCX. Install python-docx, or upload PDF/text content.") from exc
