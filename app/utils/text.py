"""Text processing helpers for extraction and scoring."""

from __future__ import annotations

import re
from collections import Counter
from typing import Optional


MASTER_SKILLS: list[str] = [
    "Python",
    "FastAPI",
    "TensorFlow",
    "Docker",
    "AWS",
    "Kubernetes",
    "Java",
    "JavaScript",
    "TypeScript",
    "SQL",
    "Django",
    "Flask",
    "React",
    "Node.js",
    "Azure",
    "GCP",
    "Machine Learning",
    "Deep Learning",
    "NLP",
    "Pandas",
    "NumPy",
    "Scikit-Learn",
    "PyTorch",
    "Data Analysis",
    "REST API",
    "Microservices",
    "CI/CD",
    "Linux",
    "Git",
    "Communication",
    "Leadership",
]


SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "python": ("python",),
    "java": ("java",),
    "javascript": ("javascript", "js"),
    "typescript": ("typescript", "ts"),
    "sql": ("sql", "postgres", "postgresql", "mysql", "sqlite"),
    "fastapi": ("fastapi",),
    "django": ("django",),
    "flask": ("flask",),
    "react": ("react", "reactjs"),
    "node.js": ("node", "nodejs", "node.js"),
    "aws": ("aws", "amazon web services"),
    "azure": ("azure",),
    "gcp": ("gcp", "google cloud"),
    "docker": ("docker",),
    "kubernetes": ("kubernetes", "k8s"),
    "machine learning": ("machine learning", "ml"),
    "deep learning": ("deep learning",),
    "nlp": ("nlp", "natural language processing"),
    "pandas": ("pandas",),
    "numpy": ("numpy",),
    "scikit-learn": ("scikit-learn", "sklearn"),
    "pytorch": ("pytorch", "torch"),
    "tensorflow": ("tensorflow",),
    "data analysis": ("data analysis", "analytics"),
    "rest api": ("rest api", "restful", "api development"),
    "microservices": ("microservices", "microservice"),
    "ci/cd": ("ci/cd", "github actions", "jenkins", "gitlab ci"),
    "linux": ("linux",),
    "git": ("git", "github", "gitlab"),
    "communication": ("communication", "stakeholder management"),
    "leadership": ("leadership", "mentoring", "team lead"),
}

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

    for canonical, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            pattern = r"(?<![a-z0-9])" + re.escape(alias.lower()) + r"(?![a-z0-9])"
            if re.search(pattern, normalized):
                found.add(DISPLAY_NAMES.get(canonical, canonical.title()))
                break

    return sorted(found)


def extract_years_experience(text: str) -> float:
    """Extract the highest explicit years-of-experience signal."""
    normalized = normalize_text(text).lower()
    patterns = [
        r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)\s+(?:of\s+)?experience",
        r"experience\s*(?:of|:)?\s*(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)",
        r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)\s+in",
    ]
    values: list[float] = []
    for pattern in patterns:
        values.extend(float(match) for match in re.findall(pattern, normalized))
    return max(values, default=0.0)


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
    normalized = {value.strip().lower() for value in values if value.strip()}
    return sorted(DISPLAY_NAMES.get(value, value.title()) for value in normalized)
