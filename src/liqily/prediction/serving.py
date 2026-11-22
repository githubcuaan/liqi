"""Build and serve the frozen, train-only post-draft research model."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import sklearn

from liqily.prediction.data import DEFAULT_DATASET, audit_dataset
from liqily.prediction.features import FeatureEncoder, SideBaseline
from liqily.prediction.final_evaluation import (
    DEFAULT_POLICY,
    fit_selected,
    load_policy,
)

ARTIFACT_DIR = Path(__file__).resolve().parents[3] / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "win_model.joblib"
METADATA_PATH = ARTIFACT_DIR / "win_model.json"


@dataclass(frozen=True)
class PredictionInput:
    team_a_heroes: frozenset[str]
    team_b_heroes: frozenset[str]
    team_a_side: str
    patch_id: str


def build_artifact(
    model_path: Path = MODEL_PATH,
    metadata_path: Path = METADATA_PATH,
) -> dict:
    """Fit the locked policy only on train, then save a reproducible serving bundle."""
    policy = load_policy(DEFAULT_POLICY, DEFAULT_DATASET)
    games, issues = audit_dataset(DEFAULT_DATASET)
    if issues:
        raise ValueError(f"Dataset audit failed with {len(issues)} issues")
    encoder, model = fit_selected(games["train"])
    baseline = SideBaseline.fit(games["train"])
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"encoder": encoder, "model": model, "baseline": baseline}, model_path)
    metadata = {
        "dataset_version": policy.dataset_version,
        "model_name": policy.model_name,
        "policy": json.loads(DEFAULT_POLICY.read_text(encoding="utf-8")),
        "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "sklearn_version": sklearn.__version__,
        "train_games": len(games["train"]),
        "feature_count": len(encoder.feature_names),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


class WinPredictor:
    def __init__(
        self, model_path: Path = MODEL_PATH, metadata_path: Path = METADATA_PATH
    ):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        policy = load_policy(DEFAULT_POLICY, DEFAULT_DATASET)
        if metadata["policy"] != json.loads(DEFAULT_POLICY.read_text(encoding="utf-8")):
            raise ValueError("Artifact policy mismatch")
        if metadata["dataset_version"] != policy.dataset_version:
            raise ValueError("Artifact dataset mismatch")
        if metadata["sklearn_version"] != sklearn.__version__:
            raise ValueError("Artifact scikit-learn version mismatch")
        if hashlib.sha256(model_path.read_bytes()).hexdigest() != metadata["model_sha256"]:
            raise ValueError("Artifact checksum mismatch")
        # Only load our locally built, verified joblib; never accept uploaded pickle.
        bundle = joblib.load(model_path)
        self.encoder: FeatureEncoder = bundle["encoder"]
        self.model = bundle["model"]
        self.baseline: SideBaseline = bundle["baseline"]
        if len(self.encoder.feature_names) != metadata["feature_count"]:
            raise ValueError("Artifact feature schema mismatch")
        self.metadata = metadata

    def predict(
        self, team_a: list[str], team_b: list[str], side: str, patch: str
    ) -> dict:
        game = PredictionInput(
            team_a_heroes=frozenset(team_a),
            team_b_heroes=frozenset(team_b),
            team_a_side=side,
            patch_id=patch,
        )
        if list(self.model.classes_) != [0, 1]:
            raise ValueError("Expected binary model classes [0, 1]")
        probability = float(self.model.predict_proba(self.encoder.transform([game]))[0, 1])
        baseline = self.baseline.predict_proba([game])[0]
        return {
            "team_a_win_probability": probability,
            "side_baseline_probability": baseline,
            "predicted_winner": "A" if probability >= 0.5 else "B",
            "unknown_categories": self.encoder.unknown_categories(game),
            "model_version": self.metadata["model_name"],
            "dataset_version": self.metadata["dataset_version"],
            "research_only": True,
            "limitations": (
                "Mô hình chưa vượt baseline theo phe trên tập test; "
                "không dùng như dự đoán chắc chắn hoặc cho patch khác."
            ),
        }


if __name__ == "__main__":
    print(json.dumps(build_artifact(), ensure_ascii=False, indent=2))
