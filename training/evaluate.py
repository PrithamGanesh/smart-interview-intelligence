"""Evaluate the blueprint success-prediction model."""

from __future__ import annotations

import argparse
from pathlib import Path

from training.train import education_to_score


def main() -> None:
    """Run model evaluation against a labeled CSV."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="training/data/candidate_success.csv")
    parser.add_argument("--model", default="training/data/success_model.json")
    args = parser.parse_args()

    import pandas as pd
    from sklearn.metrics import accuracy_score, roc_auc_score
    from xgboost import XGBClassifier

    if not Path(args.data).exists():
        raise FileNotFoundError(f"Evaluation dataset not found: {args.data}")
    if not Path(args.model).exists():
        raise FileNotFoundError(f"Model file not found: {args.model}")

    dataset = pd.read_csv(args.data)
    dataset["education_score"] = dataset["education"].fillna("").map(education_to_score)
    features = dataset[["skill_score", "experience", "education_score"]]
    target = dataset["hired"]

    model = XGBClassifier()
    model.load_model(args.model)
    probabilities = model.predict_proba(features)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    print(
        {
            "accuracy": round(float(accuracy_score(target, predictions)), 4),
            "roc_auc": round(float(roc_auc_score(target, probabilities)), 4),
        }
    )


if __name__ == "__main__":
    main()
