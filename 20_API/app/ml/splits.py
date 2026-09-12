"""Chronological dataset splitting with label-overlap embargo controls."""

from dataclasses import dataclass
from typing import Sequence

from app.ml.contracts import TrainingExample


@dataclass(frozen=True)
class DatasetSplit:
    """Ordered train/validation/test partitions."""

    train: tuple[TrainingExample, ...]
    validation: tuple[TrainingExample, ...]
    test: tuple[TrainingExample, ...]


def chronological_split(
    examples: Sequence[TrainingExample],
    train_ratio: float = 0.60,
    validation_ratio: float = 0.20,
    test_ratio: float = 0.20,
    embargo_bars: int = 0,
) -> DatasetSplit:
    """Split without shuffling and leave an embargo between partitions.

    ``embargo_bars`` should be at least the forward-label horizon when labels
    overlap across adjacent observations. The embargo rows are discarded,
    not reassigned to another split.
    """
    if not examples:
        raise ValueError("examples cannot be empty")
    if any(r <= 0 for r in (train_ratio, validation_ratio, test_ratio)):
        raise ValueError("split ratios must be positive")
    if abs(train_ratio + validation_ratio + test_ratio - 1.0) > 1e-9:
        raise ValueError("split ratios must sum to 1")
    if embargo_bars < 0:
        raise ValueError("embargo_bars cannot be negative")

    ordered = list(examples)
    previous = None
    for example in ordered:
        timestamp = example.row.event_time
        if timestamp.tzinfo is None:
            raise ValueError("example timestamps must be timezone-aware")
        if previous is not None and timestamp <= previous:
            raise ValueError("examples must be strictly chronological")
        previous = timestamp

    n = len(ordered)
    train_end = int(n * train_ratio)
    validation_end = train_end + int(n * validation_ratio)
    if train_end < 1 or validation_end <= train_end:
        raise ValueError("dataset is too small for requested split ratios")

    validation_start = train_end + embargo_bars
    test_start = validation_end + embargo_bars
    if validation_start >= validation_end or test_start >= n:
        raise ValueError("dataset is too small for requested embargo")

    train = tuple(ordered[:train_end])
    validation = tuple(ordered[validation_start:validation_end])
    test = tuple(ordered[test_start:])
    if not validation or not test:
        raise ValueError("each dataset partition must contain at least one example")
    return DatasetSplit(train=train, validation=validation, test=test)
