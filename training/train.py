"""Train the blueprint success-prediction model.

Expected CSV columns:
candidate_id, skill_score, experience, education, hired
"""

from __future__ import annotations

import argparse
from pathlib import Path


def education_to_score(value: str) -> float:
    """Convert education text to a model feature."""
    normalized = (value or "").lower()
    if "ph" in normalized or "doctor" in normalized:
        return 1.0
    if "master" in normalized or "m.tech" in normalized or "mba" in normalized:
        return 0.85
    if "bachelor" in normalized or "b.tech" in normalized or "b.e" in normalized:
        return 0.70
    return 0.40 if normalized else 0.0


def main() -> None:
    """Run XGBoost training."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="training/data/candidate_success.csv")
    parser.add_argument("--model-out", default="training/data/success_model.json")
    args = parser.parse_args()

    import pandas as pd
    from xgboost import XGBClassifier

    data_path = Path(args.data)
    if not data_path.exists():
        raise FileNotFoundError(f"Training dataset not found: {data_path}")

    dataset = pd.read_csv(data_path)
    dataset["education_score"] = dataset["education"].fillna("").map(education_to_score)
    features = dataset[["skill_score", "experience", "education_score"]]
    target = dataset["hired"]

    model = XGBClassifier(eval_metric="logloss")
    model.fit(features, target)
    model.save_model(args.model_out)
    print(f"Saved model to {args.model_out}")


if __name__ == "__main__":
    main()
