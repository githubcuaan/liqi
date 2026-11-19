from liqily.prediction.data import Game
from liqily.prediction.features import (
    FeatureEncoder,
    MajorityBaseline,
    SideBaseline,
    labels,
)


def make_game(
    *,
    game_id="game-1",
    team_a=None,
    team_b=None,
    side="blue",
    patch="patch-1",
    win=True,
):
    return Game(
        game_id=game_id,
        series_id="series-1",
        team_a_heroes=frozenset(team_a or ["a1", "a2", "a3", "a4", "a5"]),
        team_b_heroes=frozenset(team_b or ["b1", "b2", "b3", "b4", "b5"]),
        team_a_side=side,
        patch_id=patch,
        team_a_win=win,
    )


def test_fit_uses_only_games_it_receives():
    train = [make_game()]
    encoder = FeatureEncoder.fit(train)

    assert "new-hero" not in encoder.hero_ids
    assert "new-patch" not in encoder.patch_ids


def test_hero_order_does_not_change_features():
    encoder = FeatureEncoder.fit([make_game()])

    original = make_game(team_a=["a1", "a2", "a3", "a4", "a5"])
    reordered = make_game(team_a=["a5", "a4", "a3", "a2", "a1"])

    assert encoder.transform_one(original) == encoder.transform_one(reordered)


def test_unseen_categories_do_not_change_columns():
    encoder = FeatureEncoder.fit([make_game()])
    names_before = encoder.feature_names

    unseen = make_game(
        team_a=["a1", "a2", "a3", "a4", "new-hero"],
        patch="new-patch",
    )
    values = dict(zip(encoder.feature_names, encoder.transform_one(unseen)))

    assert values["team_a_unknown_hero_count"] == 1
    assert values["patch_is_unknown"] == 1
    assert encoder.feature_names == names_before
    assert encoder.unknown_categories(unseen) == {
        "team_a_heroes": ["new-hero"],
        "team_b_heroes": [],
        "patch_id": "new-patch",
    }


def test_label_does_not_enter_features():
    encoder = FeatureEncoder.fit([make_game(win=True)])

    assert encoder.transform_one(make_game(win=True)) == (
        encoder.transform_one(make_game(win=False))
    )
    assert labels([make_game(win=True), make_game(win=False)]) == [1, 0]
    assert "team_a_win" not in encoder.feature_names


def test_majority_baseline_uses_training_labels():
    train = [make_game(win=True), make_game(win=False)]
    baseline = MajorityBaseline.fit(train)

    assert baseline.probability == 0.5
    assert baseline.predict_proba([make_game(), make_game()]) == [
        0.5,
        0.5,
    ]


def test_side_baseline_and_missing_side_fallback():
    train = [
        make_game(side="blue", win=True),
        make_game(side="blue", win=False),
    ]
    baseline = SideBaseline.fit(train)

    assert baseline.blue_probability == 0.5
    assert baseline.red_probability is None
    assert baseline.predict_proba([make_game(side="blue"), make_game(side="red")]) == [
        0.5,
        0.5,
    ]
