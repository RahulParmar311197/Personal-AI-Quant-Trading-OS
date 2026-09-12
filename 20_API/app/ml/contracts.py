"""Provider-neutral ML contracts with explicit point-in-time boundaries."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from app.ml.labels import MLLabel


@dataclass(frozen=True)
class MLFeatureRow:
    """Feature snapshot available strictly at ``event_time``."""

    event_time: datetime
    instrument_id: str
    features: Mapping[str, Decimal]

    def __post_init__(self) -> None:
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")
        if not self.instrument_id.strip():
            raise ValueError("instrument_id cannot be empty")
        if any(not name.strip() for name in self.features):
            raise ValueError("feature names cannot be empty")
        object.__setattr__(self, "features", MappingProxyType(dict(self.features)))


@dataclass(frozen=True)
class TrainingExample:
    """A feature snapshot paired with a target generated from future prices."""

    row: MLFeatureRow
    label: MLLabel


@dataclass(frozen=True)
class ModelMetadata:
    """Reproducibility metadata for a trained model artifact."""

    name: str
    version: str
    feature_names: tuple[str, ...]
    training_start: datetime
    training_end: datetime
    dataset_hash: str
    random_seed: int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.version.strip():
            raise ValueError("model name and version cannot be empty")
        if self.training_start.tzinfo is None or self.training_end.tzinfo is None:
            raise ValueError("training timestamps must be timezone-aware")
        if self.training_end <= self.training_start:
            raise ValueError("training_end must be after training_start")
        if not self.dataset_hash.strip():
            raise ValueError("dataset_hash cannot be empty")
        if any(not item.strip() for item in self.feature_names):
            raise ValueError("feature_names cannot contain empty entries")


@dataclass(frozen=True)
class Prediction:
    """Point-in-time model output; it is not a trading order."""

    event_time: datetime
    model_name: str
    model_version: str
    probabilities: Mapping[MLLabel, Decimal]
    predicted_label: MLLabel

    def __post_init__(self) -> None:
        if self.event_time.tzinfo is None:
            raise ValueError("prediction event_time must be timezone-aware")
        if not self.model_name.strip() or not self.model_version.strip():
            raise ValueError("model identity cannot be empty")
        if not self.probabilities:
            raise ValueError("probabilities cannot be empty")
        total = Decimal("0")
        for probability in self.probabilities.values():
            if not Decimal("0") <= probability <= Decimal("1"):
                raise ValueError("probabilities must be between 0 and 1")
            total += probability
        if abs(total - Decimal("1")) > Decimal("0.000001"):
            raise ValueError("probabilities must sum to 1")
        if self.predicted_label not in self.probabilities:
            raise ValueError("predicted_label must have a probability")
