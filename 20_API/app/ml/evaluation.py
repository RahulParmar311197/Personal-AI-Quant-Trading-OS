"""Dependency-light classification evaluation for held-out predictions."""

from dataclasses import dataclass
from decimal import Decimal
from math import log
from typing import Mapping, Sequence

from app.ml.labels import MLLabel

LABELS: tuple[MLLabel, ...] = ("LONG", "SHORT", "NEUTRAL")
_EPSILON = Decimal("0.000000001")


@dataclass(frozen=True)
class ClassificationMetrics:
    accuracy: Decimal
    log_loss: Decimal
    brier_score: Decimal
    confusion_matrix: Mapping[MLLabel, Mapping[MLLabel, int]]


def evaluate_predictions(
    actual: Sequence[MLLabel], probabilities: Sequence[Mapping[MLLabel, Decimal]]
) -> ClassificationMetrics:
    """Evaluate probabilities without fitting or tuning on the evaluation set."""
    if not actual or len(actual) != len(probabilities):
        raise ValueError("actual and probabilities must be non-empty and equal length")

    matrix = {a: {p: 0 for p in LABELS} for a in LABELS}
    correct = 0
    log_loss_total = Decimal("0")
    brier_total = Decimal("0")

    for truth, distribution in zip(actual, probabilities):
        if truth not in LABELS:
            raise ValueError(f"unknown label: {truth}")
        if any(label not in LABELS for label in distribution):
            raise ValueError("probability distribution contains unknown label")
        total = sum(distribution.get(label, Decimal("0")) for label in LABELS)
        if any(p < 0 or p > 1 for p in distribution.values()) or total != Decimal("1"):
            raise ValueError("probabilities must be in [0, 1] and sum to 1")
        predicted = max(LABELS, key=lambda label: distribution.get(label, Decimal("0")))
        matrix[truth][predicted] += 1
        correct += int(predicted == truth)
        true_probability = max(distribution.get(truth, Decimal("0")), _EPSILON)
        log_loss_total += Decimal(str(-log(float(true_probability))))
        brier_total += sum(
            (distribution.get(label, Decimal("0")) - Decimal(int(label == truth))) ** 2
            for label in LABELS
        )

    count = Decimal(len(actual))
    return ClassificationMetrics(
        accuracy=Decimal(correct) / count,
        log_loss=log_loss_total / count,
        brier_score=brier_total / count,
        confusion_matrix=matrix,
    )
