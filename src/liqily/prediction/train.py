"""Fit train-only models and compare them on validation."""

import json
import sys
from dataclasses import dataclass

import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from liqily.prediction.data import DEFAULT_DATASET, Game, audit_dataset
from liqily.prediction.evaluate import evaluate_probabilities
from liqily.prediction.features import (
    FeatureEncoder,
    MajorityBaseline,
    SideBaseline,
    labels,
)


@dataclass
class Comparison:
    encoder: FeatureEncoder
    fitted_models: dict[str, "Classifier"]
    results: list[dict]
    best_model_name: str


Classifier = LogisticRegression | RandomForestClassifier


def candidate_models() -> dict[str, Classifier]:
    """Return a small, predefined comparison set."""
    return {
        "logistic_C_0.1": LogisticRegression(
            C=0.1,
            solver="liblinear",
            max_iter=2000,
            random_state=42,
        ),
        "logistic_C_1": LogisticRegression(
            C=1.0,
            solver="liblinear",
            max_iter=2000,
            random_state=42,
        ),
        "forest_depth_3": RandomForestClassifier(
            n_estimators=200,
            max_depth=3,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=1,
        ),
        "forest_depth_5": RandomForestClassifier(
            n_estimators=200,
            max_depth=5,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=1,
        ),
    }


def compare_on_validation(
    train_games: list[Game], validation_games: list[Game]
) -> Comparison:
    """Fit on train; evaluate and rank on validation only."""
    if not train_games or not validation_games:
        raise ValueError("Train and validation games must not be empty")
    if len({game.team_a_win for game in train_games}) != 2:
        raise ValueError("Training games must contain both outcome classes")

    encoder = FeatureEncoder.fit(train_games)

    X_train = encoder.transform(train_games)
    X_validation = encoder.transform(validation_games)
    y_train = labels(train_games)
    y_validation = labels(validation_games)

    results: list[dict] = []
    fitted_models: dict[str, Classifier] = {}

    def add_result(name: str, probabilities: list[float]) -> None:
        results.append(
            {
                "name": name,
                **evaluate_probabilities(y_validation, probabilities),
            }
        )

    # Baselines learn their rates from train, not validation.
    majority = MajorityBaseline.fit(train_games)
    side = SideBaseline.fit(train_games)
    add_result("majority_baseline", majority.predict_proba(validation_games))
    add_result("side_baseline", side.predict_proba(validation_games))

    for name, model in candidate_models().items():
        model.fit(X_train, y_train)
        probability_matrix = np.asarray(model.predict_proba(X_validation), dtype=float)
        if probability_matrix.shape != (len(validation_games), 2):
            raise ValueError(f"Unexpected probability shape for {name}")
        probabilities: list[float] = probability_matrix[:, 1].tolist()
        add_result(name, probabilities)
        fitted_models[name] = model

    # Rank only trained models; keep baselines in the comparison table.
    model_results = [result for result in results if result["name"] in fitted_models]

    best = min(
        model_results,
        key=lambda result: (
            result["brier"],
            result["log_loss"],
            result["name"],
        ),
    )

    return Comparison(
        encoder=encoder,
        fitted_models=fitted_models,
        results=results,
        best_model_name=best["name"],
    )


def main() -> None:
    games, issues = audit_dataset(DEFAULT_DATASET)
    if issues:
        raise ValueError(f"Dataset audit failed with {len(issues)} issue(s)")

    comparison = compare_on_validation(games["train"], games["validation"])

    schema = json.loads(
        (DEFAULT_DATASET / "feature_schema.json").read_text(encoding="utf-8")
    )
    print("Dataset version:", schema["dataset_version"])
    print("Python version:", sys.version.split()[0])
    print("NumPy version:", np.__version__)
    print("scikit-learn version:", sklearn.__version__)
    print("Training games:", len(games["train"]))
    print("Validation games:", len(games["validation"]))
    print("Feature count:", len(comparison.encoder.feature_names))
    print("Candidate settings (random_state=42):")
    for name, model in candidate_models().items():
        params = model.get_params()
        keys = (
            ("C", "solver", "max_iter", "random_state")
            if isinstance(model, LogisticRegression)
            else ("n_estimators", "max_depth", "min_samples_leaf", "random_state", "n_jobs")
        )
        print(f"  {name}: {', '.join(f'{key}={params[key]}' for key in keys)}")
    print("Validation results (lower Brier score is better):")
    for result in sorted(comparison.results, key=lambda row: row["brier"]):
        print(
            f'{result["name"]:20} '
            f'Brier={result["brier"]:.4f} '
            f'LogLoss={result["log_loss"]:.4f} '
            f'Accuracy={result["accuracy"]:.4f} '
            f'BalancedAccuracy={result["balanced_accuracy"]:.4f}'
        )
    print("Best trained model by validation Brier:", comparison.best_model_name)


if __name__ == "__main__":
    main()
