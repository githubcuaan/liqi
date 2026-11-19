import pytest

from liqily.prediction.data import Game
from liqily.prediction.features import FeatureEncoder, MajorityBaseline, SideBaseline


def game(side: str, win: bool) -> Game:
    return Game(
        game_id="game",
        series_id="series",
        team_a_heroes=frozenset({"a1", "a2", "a3", "a4", "a5"}),
        team_b_heroes=frozenset({"b1", "b2", "b3", "b4", "b5"}),
        team_a_side=side,
        patch_id="patch",
        team_a_win=win,
    )


def test_majority_baseline_fits_training_labels():
    baseline = MajorityBaseline.fit([game("blue", True), game("red", False)])

    assert baseline.probability == 0.5
    assert baseline.predict_proba([game("blue", False), game("red", True)]) == [
        0.5,
        0.5,
    ]


def test_majority_baseline_rejects_empty_training_set():
    with pytest.raises(ValueError, match="Training games must not be empty"):
        MajorityBaseline.fit([])


def test_side_baseline_uses_majority_prior_when_side_is_absent():
    baseline = SideBaseline.fit([game("blue", True), game("blue", False)])

    assert baseline.prior == 0.5
    assert baseline.blue_probability == 0.5
    assert baseline.red_probability is None
    assert baseline.predict_proba([game("red", True)]) == [0.5]


def test_feature_names_match_vector_width_for_known_and_unseen_patch():
    train_game = game("blue", True)
    encoder = FeatureEncoder.fit([train_game])
    unseen_game = Game(
        game_id="unseen",
        series_id="series-2",
        team_a_heroes=train_game.team_a_heroes,
        team_b_heroes=train_game.team_b_heroes,
        team_a_side="red",
        patch_id="new-patch",
        team_a_win=False,
    )

    assert encoder.patch_ids == ("patch",)
    assert len(encoder.feature_names) == len(encoder.transform_one(train_game))
    assert len(encoder.feature_names) == len(encoder.transform_one(unseen_game))
    assert dict(zip(encoder.feature_names, encoder.transform_one(unseen_game)))[
        "patch_is_unknown"
    ] == 1
