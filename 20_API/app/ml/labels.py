"""Deterministic forward-return labels for supervised learning.

This module is intentionally the only future-aware stage of the V1 dataset
pipeline. Features must be constructed independently from data available at
their own event time; generated labels are never valid model inputs.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Sequence

from app.market_data.contracts import HistoricalBar

MLLabel = Literal["LONG", "SHORT", "NEUTRAL"]


@dataclass(frozen=True)
class LabelConfig:
    """Forward-return classification parameters."""

    horizon_bars: int = 5
    return_threshold: Decimal = Decimal("0.002")

    def __post_init__(self) -> None:
        if self.horizon_bars < 1:
            raise ValueError("horizon_bars must be at least 1")
        if self.return_threshold <= 0:
            raise ValueError("return_threshold must be positive")


def generate_labels(
    bars: Sequence[HistoricalBar], config: LabelConfig | None = None
) -> list[MLLabel | None]:
    """Generate labels aligned to each bar using a strictly future close.

    The final ``horizon_bars`` observations have no label because their future
    outcome is not yet observable. This function must run after point-in-time
    feature construction and must never feed labels back into feature rows.
    """
    cfg = config or LabelConfig()
    ordered = list(bars)
    previous = None
    for bar in ordered:
        if bar.event_time.tzinfo is None:
            raise ValueError("bar event_time must be timezone-aware")
        if bar.close <= 0:
            raise ValueError("bar close must be positive")
        if previous is not None and bar.event_time <= previous:
            raise ValueError("bars must be strictly increasing")
        previous = bar.event_time

    labels: list[MLLabel | None] = [None] * len(ordered)
    for index, current in enumerate(ordered):
        future_index = index + cfg.horizon_bars
        if future_index >= len(ordered):
            continue
        future_close = ordered[future_index].close
        forward_return = future_close / current.close - Decimal("1")
        if forward_return >= cfg.return_threshold:
            labels[index] = "LONG"
        elif forward_return <= -cfg.return_threshold:
            labels[index] = "SHORT"
        else:
            labels[index] = "NEUTRAL"
    return labels
