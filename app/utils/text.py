"""Text processing helpers for extraction and scoring."""

from __future__ import annotations

import re
from collections import Counter
from typing import Optional

from app.utils.taxonomy import alias_to_skill, load_skill_taxonomy, normalize_skills


MASTER_SKILLS: list[str] = [str(item["name"]) for item in load_skill_taxonomy()]
DISPLAY_NAMES = {skill.lower(): skill for skill in MASTER_SKILLS}


STOPWORDS = {
    "and",
    "are",
    "but",
    "for",
    "from",
    "has",
    "have",
    "into",
    "our",
    "the",
    "this",
    "that",
    "with",
    "you",
    "your",
}


EDUCATION_PATTERNS = [
    r"\b(b\.?\s?tech|bachelor(?:'s)?(?: of [a-z ]+)?|b\.?\s?e\.?)\b",
    r"\b(m\.?\s?tech|master(?:'s)?(?: of [a-z ]+)?|m\.?\s?s\.?)\b",
    r"\b(ph\.?\s?d|doctorate)\b",
    r"\b(mba)\b",
]


def normalize_text(text: str) -> str:
    """Normalize whitespace for downstream processing."""
    return re.sub(r"\s+", " ", text or "").strip()


def tokenize(text: str) -> list[str]:
    """Return lowercase word tokens."""
    return re.findall(r"[a-zA-Z][a-zA-Z0-9.+#/-]*", text.lower())


def extract_skills(text: str) -> list[str]:
    """Extract known skills from unstructured text.

    If spaCy is installed, this function can be swapped to PhraseMatcher
    without changing service code. The fallback regex matcher uses the same
    master skill database from the blueprint.
    """
    normalized = f" {normalize_text(text).lower()} "
    found: set[str] = set()

    for alias, canonical in alias_to_skill().items():
        pattern = r"(?<![a-z0-9])" + re.escape(alias.lower()) + r"(?![a-z0-9])"
        if re.search(pattern, normalized):
            found.add(canonical)

    return sorted(found)


def extract_experience_range(text: str) -> tuple[float, float]:
    """Extract a min/max years-of-experience range from resume or JD text."""
    normalized = normalize_text(text).lower().replace("–", "-").replace("—", "-")
    ranges = re.findall(
        r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)",
        normalized,
    )
    if ranges:
        values = [(float(low), float(high)) for low, high in ranges]
        return min(low for low, _ in values), max(high for _, high in values)

    values = _experience_values(normalized)
    if values:
        highest = max(values)
        return highest, highest
    return 0.0, 0.0


def extract_years_experience(text: str) -> float:
    """Extract the highest explicit years-of-experience signal."""
    normalized = normalize_text(text).lower()
    low, high = extract_experience_range(normalized)
    if high > low:
        return low
    if high:
        return high
    return max(_experience_values(normalized), default=0.0)


def _experience_values(normalized: str) -> list[float]:
    patterns = [
        r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)\s+(?:of\s+)?experience",
        r"experience\s*(?:of|:)?\s*(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)",
        r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)\s+in",
    ]
    values: list[float] = []
    for pattern in patterns:
        values.extend(float(match) for match in re.findall(pattern, normalized))
    return values


def extract_email(text: str) -> Optional[str]:
    """Extract the first email address from text."""
    match = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text or "")
    return match.group(0) if match else None


def extract_candidate_name(text: str, fallback: str = "Unknown Candidate") -> str:
    """Infer a candidate name from the first useful resume line."""
    for line in (text or "").splitlines():
        cleaned = line.strip()
        if not cleaned or "@" in cleaned or len(cleaned) > 80:
            continue
        if re.search(r"\d", cleaned):
            continue
        if cleaned.lower() in {"resume", "curriculum vitae", "cv"}:
            continue
        return cleaned
    return fallback


def extract_education(text: str) -> str:
    """Extract a simple education signal."""
    normalized = normalize_text(text)
    for pattern in EDUCATION_PATTERNS:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return match.group(0).replace("  ", " ").strip()
    return ""


def extract_section_items(text: str, section_names: tuple[str, ...], limit: int = 5) -> list[str]:
    """Extract lightweight section items for projects and certifications."""
    lines = [line.strip(" -\t") for line in (text or "").splitlines() if line.strip()]
    items: list[str] = []
    collecting = False
    headings = {"skills", "experience", "education", "projects", "certifications", "certificates", "summary"}
    targets = {name.lower() for name in section_names}

    for line in lines:
        label = line.rstrip(":").lower()
        if label in targets:
            collecting = True
            continue
        if collecting and label in headings and label not in targets:
            collecting = False
        if collecting and label not in targets:
            items.append(line)

    if not items:
        for name in section_names:
            pattern = re.compile(rf"{re.escape(name)}\s*:\s*([^.\n]+)", flags=re.IGNORECASE)
            items.extend(match.strip() for match in pattern.findall(text or ""))

    return items[:limit]


def extract_keywords(text: str, limit: int = 12) -> list[str]:
    """Extract frequent meaningful words for dashboards and question context."""
    tokens = [token for token in tokenize(text) if len(token) > 2 and token not in STOPWORDS]
    counts = Counter(tokens)
    return [word for word, _ in counts.most_common(limit)]


def unique_sorted(values: list[str]) -> list[str]:
    """Return case-insensitive unique sorted strings."""
    return normalize_skills(values)
