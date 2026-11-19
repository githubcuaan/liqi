import pytest

from liqily.prediction.evaluate import evaluate_probabilities


def test_correct_probabilities_score_better_than_confident_wrong_ones():
    good = evaluate_probabilities([1, 0], [0.9, 0.1])
    bad = evaluate_probabilities([1, 0], [0.1, 0.9])

    assert good["brier"] < bad["brier"]
    assert good["log_loss"] < bad["log_loss"]
    assert good["accuracy"] == 1.0
    assert good["balanced_accuracy"] == 1.0


def test_balanced_accuracy_penalizes_predicting_only_one_class():
    metrics = evaluate_probabilities([1, 1, 0], [0.8, 0.8, 0.8])

    assert metrics["accuracy"] == pytest.approx(2 / 3)
    assert metrics["balanced_accuracy"] == 0.5


@pytest.mark.parametrize(
    ("truth", "probabilities"),
    [
        ([], []),
        ([1, 0], [0.5]),
        ([1], [1.2]),
        ([0], [-0.1]),
    ],
)
def test_rejects_invalid_inputs(truth, probabilities):
    with pytest.raises(ValueError):
        evaluate_probabilities(truth, probabilities)
