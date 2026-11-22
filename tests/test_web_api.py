"""Contract tests against real, frozen source artifacts and the unified API."""

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from liqily.api.app import app, services
from liqily.draft.vendor.liqi_draft import DraftRecommender
from liqily.mining.apriori_miner import AprioriMiner
from liqily.mining.fpgrowth_miner import FPGrowthMiner
from liqily.mining.preprocessing import DataPreprocessor
from liqily.prediction.data import DEFAULT_DATASET, audit_dataset
from liqily.prediction.final_evaluation import fit_selected, win_probabilities
from liqily.prediction.serving import (
    METADATA_PATH, MODEL_PATH, PredictionInput, WinPredictor, build_artifact,
)


@pytest.fixture(scope="module")
def client():
    if not MODEL_PATH.is_file() or not METADATA_PATH.is_file():
        build_artifact()
    services.cache_clear()
    return TestClient(app)


def test_frozen_inputs_are_identical_to_manifest():
    manifest = json.loads((DEFAULT_DATASET / "release-manifest.json").read_text())
    for name in ("csv/association_train.csv", "csv/heroes.csv", "csv/train.csv"):
        content = (DEFAULT_DATASET / name).read_bytes()
        assert hashlib.sha256(content).hexdigest() == manifest["files"][name]


def test_imported_miners_agree_on_training_transactions():
    transactions, processed = DataPreprocessor().process_transactions()
    assert len(transactions) == 462 == len(processed)
    params = dict(min_support=0.01, min_confidence=0.5, min_lift=1, max_heroes=5)
    apriori, _ = AprioriMiner(**params).run_mining(transactions)
    fpgrowth, _ = FPGrowthMiner(**params).run_mining(transactions)
    assert {frozenset(row) for row in apriori.itemsets} == {
        frozenset(row) for row in fpgrowth.itemsets
    }


def test_catalog_overview_and_draft_match_handoff(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    overview = client.get("/api/v1/overview").json()
    assert (overview["total_games"], overview["total_teams"]) == (231, 462)
    catalog = client.get("/api/v1/catalog/heroes").json()
    assert len(catalog) >= 83
    request = {"action": "pick", "own_picks": [catalog[0]["hero_id"]], "k": 5}
    expected = DraftRecommender().recommend(request)
    actual = client.post("/api/v1/draft/recommend", json=request)
    assert actual.status_code == 200
    assert actual.json() == expected
    assert client.post("/api/v1/draft/recommend", json={
        **request, "banned": request["own_picks"]
    }).status_code == 422
    ban_request = {"action": "ban", "own_picks": request["own_picks"], "k": 5}
    ban_result = client.post("/api/v1/draft/recommend", json=ban_request)
    assert ban_result.status_code == 200
    assert ban_result.json() == DraftRecommender().recommend(ban_request)
    assert ban_result.json()["score_type"] == "observed_train_ban_game_frequency"
    assert client.post("/api/v1/draft/recommend", json={"action": "pick", "k": True}).status_code == 422


def test_mining_comparison_and_csv(client):
    request = {"min_support": 0.01}
    result = client.post("/api/v1/mining/run", json={**request, "algorithm": "fpgrowth"})
    assert result.status_code == 200
    assert result.json()["win_rules_count"] > 0
    assert all(row["result"] in ("WIN", "LOSE") for row in result.json()["rules"])
    comparison = client.post("/api/v1/mining/compare", json=request)
    assert comparison.status_code == 200
    assert comparison.json()["apriori"]["frequent_itemsets_count"] == comparison.json()["fpgrowth"]["frequent_itemsets_count"]
    csv_response = client.get("/api/v1/reports/fpgrowth_rules.csv?min_support=0.01")
    assert csv_response.status_code == 200
    assert "antecedents" in csv_response.text
    assert client.post("/api/v1/mining/run", json={"min_support": 0}).status_code == 422
    pairs = client.get("/api/v1/compositions?size=2&min_matches=5")
    assert pairs.status_code == 200
    assert all(row["size"] == 2 and row["matches"] >= 5 for row in pairs.json()["compositions"])
    assert client.get("/api/v1/reports/comparison.csv?min_support=0.01").status_code == 200


def test_prediction_matches_train_only_model_and_validates_input(client):
    games, issues = audit_dataset(DEFAULT_DATASET)
    assert not issues
    game = games["validation"][0]
    request = {
        "team_a_heroes": sorted(game.team_a_heroes),
        "team_b_heroes": sorted(game.team_b_heroes),
        "team_a_side": game.team_a_side,
        "patch_id": game.patch_id,
    }
    result = client.post("/api/v1/predictions/win", json=request)
    assert result.status_code == 200
    encoder, model = fit_selected(games["train"])
    assert result.json()["team_a_win_probability"] == pytest.approx(
        win_probabilities(model, encoder, [game])[0]
    )
    assert result.json()["research_only"] is True
    assert "team_a_win" not in PredictionInput.__dataclass_fields__
    assert client.post("/api/v1/predictions/win", json={
        **request, "team_b_heroes": request["team_a_heroes"]
    }).status_code == 422
    assert client.post("/api/v1/predictions/win", json={
        **request, "team_a_heroes": ["unknown"] + request["team_a_heroes"][1:]
    }).status_code == 422
    unseen_patch = client.post("/api/v1/predictions/win", json={
        **request, "patch_id": "aov:unknown-patch"
    })
    assert unseen_patch.status_code == 200
    assert unseen_patch.json()["unknown_categories"]["patch_id"] == "aov:unknown-patch"


def test_serving_rejects_tampered_metadata(tmp_path):
    model_path = tmp_path / "model.joblib"
    metadata_path = tmp_path / "model.json"
    build_artifact(model_path, metadata_path)
    assert WinPredictor(model_path, metadata_path).metadata["train_games"] == 231
    metadata = json.loads(metadata_path.read_text())
    metadata["model_sha256"] = "tampered"
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="checksum"):
        WinPredictor(model_path, metadata_path)


def test_built_frontend_is_served(client):
    dist = Path(__file__).resolve().parents[1] / "web" / "dist"
    if not dist.is_dir():
        pytest.skip("Run npm run build to check production static delivery")
    response = client.get("/")
    assert response.status_code == 200
    assert "Liqily" in response.text
    logos = sorted((dist / "assets").glob("liqily*.png"))
    assert len(logos) == 2
    assert all(client.get(f"/assets/{logo.name}").status_code == 200 for logo in logos)
