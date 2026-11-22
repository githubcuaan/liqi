"""Evaluate binary win probalilities."""

from collections.abc import Sequence

from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
)


def evaluate_probabilities(
    y_true: Sequence[int], probabilities: Sequence[float]
) -> dict[str, float]:
    """Compute probalility and threshold-based metrics."""
    if not y_true or len(y_true) != len(probabilities):
        raise ValueError("Labels and probabilities must have equal nonzero length")

    if any(not 0.0 <= probalilities <= 1.0 for probalilities in probabilities):
        raise ValueError("Probalilities must be between 0 and 1")

    predictions = [int(probalility >= 0.5) for probalility in probabilities]

    return {
        "brier": float(brier_score_loss(y_true, probabilities)),
        "log_loss": float(log_loss(y_true, probabilities, labels=[0, 1])),
        "accuracy": float(accuracy_score(y_true, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predictions)),
    }
