from liqily.prediction.data import Game
from liqily.prediction.train import candidate_models, compare_on_validation


def game(game_id: str, side: str, win: bool, patch: str = "patch-1") -> Game:
    return Game(
        game_id=game_id,
        series_id=game_id,
        team_a_heroes=frozenset({"a1", "a2", "a3", "a4", "a5"}),
        team_b_heroes=frozenset({"b1", "b2", "b3", "b4", "b5"}),
        team_a_side=side,
        patch_id=patch,
        team_a_win=win,
    )


def test_comparison_fits_train_only_and_includes_baselines():
    train = [
        game("train-1", "blue", True),
        game("train-2", "red", False),
        game("train-3", "blue", False),
        game("train-4", "red", True),
    ]
    validation = [
        game("validation-1", "blue", False, "new-patch"),
        game("validation-2", "red", True, "new-patch"),
    ]

    result = compare_on_validation(train, validation)
    scores = {row["name"]: row for row in result.results}

    assert len(result.results) == 6
    assert set(result.fitted_models) == set(candidate_models())
    assert result.best_model_name in result.fitted_models
    assert {"majority_baseline", "side_baseline"} <= scores.keys()
    assert result.encoder.patch_ids == ("patch-1",)
    assert scores["majority_baseline"]["brier"] == 0.25
    assert all(0 <= row["brier"] <= 1 for row in result.results)


def test_validation_labels_do_not_change_fitted_models():
    train = [game(f"train-{i}", "blue" if i % 2 else "red", i % 2 == 1)
             for i in range(6)]
    validation_lost = [
        game("validation-1", "blue", False, "new-patch"),
        game("validation-2", "red", True, "new-patch"),
    ]
    validation_won = [
        game("validation-1", "blue", True, "new-patch"),
        game("validation-2", "red", False, "new-patch"),
    ]

    first = compare_on_validation(train, validation_lost)
    second = compare_on_validation(train, validation_won)

    assert first.encoder == second.encoder
    for name in first.fitted_models:
        assert (
            first.fitted_models[name]
            .predict_proba(first.encoder.transform(validation_lost))
            .tolist()
            == second.fitted_models[name]
            .predict_proba(second.encoder.transform(validation_won))
            .tolist()
        )
