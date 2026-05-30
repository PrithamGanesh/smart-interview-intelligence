"""Candidate success prediction.

The production blueprint targets XGBoostClassifier. This module exposes the
same prediction boundary and uses a transparent fallback until a trained model
artifact is supplied.
"""

from __future__ import annotations

from typing import Optional

from app.core.config import get_settings


def predict_success_probability(
    skill_score: float,
    experience: float,
    education: str = "",
    model_path: Optional[str] = None,
) -> dict[str, object]:
    """Predict success probability as a 0-100 value."""
    model = _load_xgboost_model(model_path)
    features = [[skill_score, experience, _education_score(education)]]
    if model is not None:
        probability = float(model.predict_proba(features)[0][1]) * 100
        return {"success_probability": round(probability, 2), "model": get_settings().success_model_name}

    experience_component = min(experience / 5.0, 1.0) * 25
    education_component = _education_score(education) * 15
    probability = min(skill_score * 0.60 + experience_component + education_component, 100)
    return {"success_probability": round(probability, 2), "model": "heuristic-fallback"}


def _load_xgboost_model(model_path: Optional[str]):
    if not model_path:
        return None
    try:
        from xgboost import XGBClassifier

        model = XGBClassifier()
        model.load_model(model_path)
        return model
    except Exception:
        return None


def _education_score(education: str) -> float:
    value = (education or "").lower()
    if "ph" in value or "doctor" in value:
        return 1.0
    if "master" in value or "m.tech" in value or "mba" in value:
        return 0.85
    if "bachelor" in value or "b.tech" in value or "b.e" in value:
        return 0.70
    return 0.40 if value else 0.0
