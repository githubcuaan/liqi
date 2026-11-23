"""Freeze a validation policy before evaluating the held-out test set."""

import argparse
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
from sklearn.metrics import confusion_matrix

from liqily.prediction.data import DEFAULT_DATASET, Game, audit_dataset
from liqily.prediction.evaluate import evaluate_probabilities
from liqily.prediction.features import (
    FeatureEncoder,
    MajorityBaseline,
    SideBaseline,
    labels,
)
from liqily.prediction.train import Classifier, candidate_models

DEFAULT_POLICY = Path(__file__).resolve().parents[3] / "docs" / "report" / "model_selection.json"
SELECTED_MODEL = "forest_depth_3"


@dataclass(frozen=True)
class FinalPolicy:
    dataset_version: str
    model_name: str
    selection_metric: str
    threshold: float
    symmetrize: bool
    fit_partition: str
    selection_partition: str


def dataset_version(dataset_dir: Path) -> str:
    """Read the immutable snapshot identity from its feature schema."""
    schema = json.loads(
        (dataset_dir / "feature_schema.json").read_text(encoding="utf-8")
    )
    return schema["dataset_version"]


def load_policy(path: Path, dataset_dir: Path) -> FinalPolicy:
    """Reject unapproved settings before loading test games."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if set(raw) != set(FinalPolicy.__dataclass_fields__):
        raise ValueError("Policy must contain exactly the required fields")
    policy = FinalPolicy(**raw)
    if policy.dataset_version != dataset_version(dataset_dir):
        raise ValueError("Policy dataset version does not match the snapshot")
    if policy.model_name != SELECTED_MODEL or policy.model_name not in candidate_models():
        raise ValueError("Policy model is not the selected validation model")
    if policy.selection_metric != "validation_brier":
        raise ValueError("Policy selection metric must be validation_brier")
    if type(policy.threshold) is not float or policy.threshold != 0.5:
        raise ValueError("Policy threshold must be 0.5")
    if type(policy.symmetrize) is not bool:
        raise ValueError("Policy symmetrize must be a boolean")
    if policy.fit_partition != "train" or policy.selection_partition != "validation":
        raise ValueError("Policy partitions must be train and validation")
    return policy


def swap_teams(game: Game) -> Game:
    """Swap team compositions, side and label; keep the patch unchanged."""
    return replace(
        game,
        team_a_heroes=game.team_b_heroes,
        team_b_heroes=game.team_a_heroes,
        team_a_side="red" if game.team_a_side == "blue" else "blue",
        team_a_win=not game.team_a_win,
    )


def win_probabilities(
    model: Classifier, encoder: FeatureEncoder, games: list[Game]
) -> np.ndarray:
    """Predict P(team A wins) for games using a fitted train-only model."""
    matrix = np.asarray(model.predict_proba(encoder.transform(games)), dtype=float)
    if matrix.shape != (len(games), 2):
        raise ValueError("Expected one binary probability pair per game")
    if list(model.classes_) != [0, 1]:
        raise ValueError("Expected binary classes [0, 1]")
    return matrix[:, 1]


def symmetrize_probabilities(p: np.ndarray, p_swapped: np.ndarray) -> np.ndarray:
    """Make predictions consistent under swapping team A and team B."""
    if p.shape != p_swapped.shape or p.ndim != 1:
        raise ValueError("Probability vectors must have the same one-dimensional shape")
    return (p + 1 - p_swapped) / 2


def fit_selected(train_games: list[Game]) -> tuple[FeatureEncoder, Classifier]:
    """Fit only the selected candidate and its encoder on train."""
    encoder = FeatureEncoder.fit(train_games)
    model = candidate_models()[SELECTED_MODEL]
    model.fit(encoder.transform(train_games), labels(train_games))
    return encoder, model


def validation_symmetry_report(
    train_games: list[Game], validation_games: list[Game]
) -> dict:
    """Check raw versus symmetric predictions using validation only."""
    encoder, model = fit_selected(train_games)
    p = win_probabilities(model, encoder, validation_games)
    p_swapped = win_probabilities(
        model, encoder, [swap_teams(game) for game in validation_games]
    )
    symmetric = symmetrize_probabilities(p, p_swapped)
    inconsistency = np.abs(p + p_swapped - 1)
    truth = labels(validation_games)
    return {
        "model_name": SELECTED_MODEL,
        "validation_games": len(validation_games),
        "raw": evaluate_probabilities(truth, p.tolist()),
        "symmetric": evaluate_probabilities(truth, symmetric.tolist()),
        "mean_swap_inconsistency": float(inconsistency.mean()),
        "max_swap_inconsistency": float(inconsistency.max()),
    }


def subgroup_summary(games: list[Game], p: list[float]) -> dict:
    """Describe test subsets without fitting, tuning, or interpreting small groups."""
    truth = labels(games)
    if not games:
        return {"games": 0, "brier": None, "accuracy": None}
    return {
        "games": len(games),
        "brier": float(np.mean([(prob - label) ** 2 for prob, label in zip(p, truth)])),
        "accuracy": float(np.mean([int(prob >= 0.5) == label for prob, label in zip(p, truth)])),
    }


def final_test_report(
    train_games: list[Game], test_games: list[Game], policy: FinalPolicy
) -> dict:
    """Evaluate a frozen policy once on held-out games; never refit on test."""
    if not train_games or not test_games:
        raise ValueError("Train and test games must not be empty")
    encoder, model = fit_selected(train_games)
    p = win_probabilities(model, encoder, test_games)
    if policy.symmetrize:
        p_swapped = win_probabilities(
            model, encoder, [swap_teams(game) for game in test_games]
        )
        p = symmetrize_probabilities(p, p_swapped)
    probabilities = p.tolist()
    truth = labels(test_games)
    majority = MajorityBaseline.fit(train_games)
    side = SideBaseline.fit(train_games)
    metrics = {
        "selected_model": evaluate_probabilities(truth, probabilities),
        "majority_baseline": evaluate_probabilities(
            truth, majority.predict_proba(test_games)
        ),
        "side_baseline": evaluate_probabilities(
            truth, side.predict_proba(test_games)
        ),
    }
    predictions = [int(probability >= policy.threshold) for probability in probabilities]
    matrix = confusion_matrix(truth, predictions, labels=[0, 1]).tolist()

    groups: dict[str, list[int]] = {
        "known_heroes_and_patch": [],
        "unseen_hero": [],
        "unseen_patch": [],
        "unseen_hero_and_patch": [],
    }
    for index, game in enumerate(test_games):
        unknown = encoder.unknown_categories(game)
        has_hero = bool(unknown["team_a_heroes"] or unknown["team_b_heroes"])
        has_patch = unknown["patch_id"] is not None
        if not has_hero and not has_patch:
            groups["known_heroes_and_patch"].append(index)
        if has_hero:
            groups["unseen_hero"].append(index)
        if has_patch:
            groups["unseen_patch"].append(index)
        if has_hero and has_patch:
            groups["unseen_hero_and_patch"].append(index)

    return {
        "policy": asdict(policy),
        "train_games": len(train_games),
        "test_games": len(test_games),
        "test_series": len({game.series_id for game in test_games}),
        "test_team_a_wins": sum(truth),
        "feature_count": len(encoder.feature_names),
        "metrics": metrics,
        "confusion_matrix": {"labels": [0, 1], "rows": matrix},
        "subgroups": {
            name: subgroup_summary(
                [test_games[i] for i in indices],
                [probabilities[i] for i in indices],
            )
            for name, indices in groups.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate policy or evaluate frozen test")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--validation", action="store_true", help="Inspect swap consistency")
    action.add_argument("--test", action="store_true", help="Evaluate frozen policy on test")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    args = parser.parse_args()

    policy = load_policy(args.policy, args.dataset) if args.test else None
    games, issues = audit_dataset(args.dataset)
    if issues:
        raise ValueError(f"Dataset audit failed with {len(issues)} issue(s)")
    report = (
        final_test_report(games["train"], games["test"], policy)
        if policy is not None
        else validation_symmetry_report(games["train"], games["validation"])
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
