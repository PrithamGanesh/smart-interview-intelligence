"""Skill taxonomy loading and normalization."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


FALLBACK_TAXONOMY = [
    {"name": "Python", "category": "language", "aliases": ["python", "python3"]},
    {"name": "FastAPI", "category": "framework", "aliases": ["fastapi"]},
    {"name": "Docker", "category": "tool", "aliases": ["docker"]},
    {"name": "AWS", "category": "cloud", "aliases": ["aws", "amazon web services"]},
    {"name": "Machine Learning", "category": "domain", "aliases": ["machine learning", "ml"]},
    {"name": "Communication", "category": "soft", "aliases": ["communication", "stakeholder management"]},
]


@lru_cache
def load_skill_taxonomy() -> list[dict[str, object]]:
    """Load the versioned skill taxonomy from data/ with a small fallback."""
    path = Path(__file__).resolve().parents[2] / "data" / "skill_taxonomy.json"
    if not path.exists():
        return FALLBACK_TAXONOMY
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return list(payload.get("skills", payload))


@lru_cache
def alias_to_skill() -> dict[str, str]:
    """Return alias-to-canonical skill lookup."""
    lookup: dict[str, str] = {}
    for item in load_skill_taxonomy():
        name = str(item["name"])
        aliases = {name, *(str(alias) for alias in item.get("aliases", []))}
        for alias in aliases:
            lookup[alias.strip().lower()] = name
    return lookup


def normalize_skill(value: str) -> str:
    """Normalize a single skill or alias to its canonical taxonomy name."""
    cleaned = value.strip().lower()
    return alias_to_skill().get(cleaned, value.strip().title())


def normalize_skills(values: list[str]) -> list[str]:
    """Normalize, deduplicate, and sort skill names."""
    return sorted({normalize_skill(value) for value in values if value and value.strip()})
