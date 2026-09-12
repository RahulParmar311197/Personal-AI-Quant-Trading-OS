"""Dependency-light probabilistic model baseline and model protocol."""

from collections import Counter
from decimal import Decimal
from typing import Protocol, Sequence

from app.ml.labels import MLLabel


class ProbabilisticClassifier(Protocol):
    """Minimal adapter boundary for sklearn/XGBoost/LightGBM/PyTorch later."""

    def fit(self, features: Sequence[dict[str, Decimal]], labels: Sequence[MLLabel]) -> None: ...

    def predict_proba(self, features: dict[str, Decimal]) -> dict[MLLabel, Decimal]: ...


class MajorityClassBaseline:
    """Deterministic majority-class baseline for measuring real model lift."""

    def __init__(self) -> None:
        self._probabilities: dict[MLLabel, Decimal] | None = None

    def fit(self, features: Sequence[dict[str, Decimal]], labels: Sequence[MLLabel]) -> None:
        if len(features) != len(labels):
            raise ValueError("features and labels must have equal length")
        if not labels:
            raise ValueError("training labels cannot be empty")
        counts = Counter(labels)
        total = Decimal(len(labels))
        self._probabilities = {
            label: Decimal(counts.get(label, 0)) / total
            for label in ("LONG", "SHORT", "NEUTRAL")
        }

    def predict_proba(self, features: dict[str, Decimal]) -> dict[MLLabel, Decimal]:
        if self._probabilities is None:
            raise RuntimeError("model must be fitted before prediction")
        return dict(self._probabilities)
