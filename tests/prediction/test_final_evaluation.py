import json

import numpy as np
import pytest

from liqily.prediction.data import Game
from liqily.prediction.final_evaluation import (
    FinalPolicy,
    final_test_report,
    load_policy,
    swap_teams,
    symmetrize_probabilities,
)


def make_game(name: str, side: str, win: bool, patch: str = "patch") -> Game:
    return Game(
        game_id=name,
        series_id=name,
        team_a_heroes=frozenset({"a1", "a2", "a3", "a4", "a5"}),
        team_b_heroes=frozenset({"b1", "b2", "b3", "b4", "b5"}),
        team_a_side=side,
        patch_id=patch,
        team_a_win=win,
    )


def policy(version: str = "version", **changes) -> dict:
    values = {
        "dataset_version": version,
        "model_name": "forest_depth_3",
        "selection_metric": "validation_brier",
        "threshold": 0.5,
        "symmetrize": False,
        "fit_partition": "train",
        "selection_partition": "validation",
    }
    values.update(changes)
    return values


def test_swapping_twice_returns_original_game():
    original = make_game("one", "blue", True)
    swapped = swap_teams(original)
    assert swapped.team_a_heroes == original.team_b_heroes
    assert swapped.team_a_side == "red"
    assert swapped.team_a_win is False
    assert swapped.patch_id == original.patch_id
    assert swap_teams(swapped) == original


def test_symmetrization_is_consistent_under_team_swap():
    p = np.array([0.8, 0.3])
    p_swapped = np.array([0.4, 0.9])
    adjusted = symmetrize_probabilities(p, p_swapped)
    adjusted_swapped = symmetrize_probabilities(p_swapped, p)

    assert np.all((adjusted >= 0) & (adjusted <= 1))
    np.testing.assert_allclose(adjusted + adjusted_swapped, np.ones(2))


def test_symmetrization_rejects_mismatched_shapes():
    with pytest.raises(ValueError):
        symmetrize_probabilities(np.array([0.5]), np.array([0.2, 0.4]))


@pytest.mark.parametrize(
    "change",
    [
        {"dataset_version": "wrong"},
        {"model_name": "forest_depth_5"},
        {"threshold": 0.6},
        {"symmetrize": "false"},
        {"selection_partition": "test"},
    ],
)
def test_policy_rejects_unfrozen_settings(tmp_path, change):
    (tmp_path / "feature_schema.json").write_text(
        json.dumps({"dataset_version": "version"})
    )
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy(**change)))
    with pytest.raises(ValueError):
        load_policy(path, tmp_path)


def test_final_report_uses_fixed_policy_on_synthetic_games():
    train = [
        make_game("train-1", "blue", True),
        make_game("train-2", "red", False),
        make_game("train-3", "red", True),
        make_game("train-4", "blue", False),
        make_game("train-5", "blue", True),
        make_game("train-6", "red", False),
    ]
    test = [
        make_game("holdout-1", "blue", False),
        make_game("holdout-2", "red", True, "new-patch"),
    ]
    frozen = FinalPolicy(**policy())
    result = final_test_report(train, test, frozen)

    assert result["train_games"] == 6
    assert result["test_games"] == 2
    assert result["confusion_matrix"]["labels"] == [0, 1]
    assert sum(map(sum, result["confusion_matrix"]["rows"])) == 2
    assert set(result["metrics"]) == {
        "selected_model",
        "majority_baseline",
        "side_baseline",
    }
    assert result["subgroups"]["unseen_patch"]["games"] == 1
