"""Deterministic point-in-time market-regime classifier.

Regime is context, not a trading decision. The classifier deliberately emits
an auditable label and component scores; strategy selection and risk remain
separate downstream responsibilities.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from app.market_data.technical import TechnicalFeatures

MarketRegime = Literal["TREND_UP", "TREND_DOWN", "RANGE", "HIGH_VOLATILITY", "UNKNOWN"]


@dataclass(frozen=True)
class RegimeConfig:
    """Thresholds for deterministic regime classification."""

    trend_return_threshold: Decimal = Decimal("0.002")
    volatility_range_threshold: Decimal = Decimal("0.02")
    volume_ratio_threshold: Decimal = Decimal("1.5")

    def __post_init__(self) -> None:
        if self.trend_return_threshold <= 0:
            raise ValueError("trend_return_threshold must be positive")
        if self.volatility_range_threshold <= 0:
            raise ValueError("volatility_range_threshold must be positive")
        if self.volume_ratio_threshold <= 0:
            raise ValueError("volume_ratio_threshold must be positive")


@dataclass(frozen=True)
class RegimeClassification:
    """Point-in-time regime result with auditable component evidence."""

    event_time: datetime
    regime: MarketRegime
    confidence: Decimal
    trend_score: Decimal
    volatility_score: Decimal
    volume_score: Decimal
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")
        if not Decimal("0") <= self.confidence <= Decimal("1"):
            raise ValueError("confidence must be between 0 and 1")
        for score_name, score in (
            ("trend_score", self.trend_score),
            ("volatility_score", self.volatility_score),
            ("volume_score", self.volume_score),
        ):
            if not Decimal("0") <= score <= Decimal("1"):
                raise ValueError(f"{score_name} must be between 0 and 1")
        if any(not reason.strip() for reason in self.reasons):
            raise ValueError("reasons cannot contain empty entries")


class RegimeEngine:
    """Classify a single point-in-time feature snapshot.

    Required warm-up features produce UNKNOWN rather than a guessed regime.
    High volatility has precedence over directional trend so that a violent
    market is not mislabeled as an ordinary trend.
    """

    def __init__(self, config: RegimeConfig | None = None) -> None:
        self.config = config or RegimeConfig()

    def classify(self, features: TechnicalFeatures) -> RegimeClassification:
        trend_score = self._trend_score(features)
        volatility_score = self._volatility_score(features)
        volume_score = self._volume_score(features)
        reasons: list[str] = []

        if features.returns is None or features.ema is None:
            return RegimeClassification(
                features.event_time.astimezone(timezone.utc),
                "UNKNOWN",
                Decimal("0"),
                trend_score,
                volatility_score,
                volume_score,
                ("insufficient warm-up data",),
            )

        if features.range_pct is not None and features.range_pct >= self.config.volatility_range_threshold:
            reasons.append("range exceeds high-volatility threshold")
            if volume_score >= Decimal("0.5"):
                reasons.append("elevated volume confirms volatility")
            return RegimeClassification(
                features.event_time.astimezone(timezone.utc),
                "HIGH_VOLATILITY",
                max(volatility_score, Decimal("0.5")),
                trend_score,
                volatility_score,
                volume_score,
                tuple(reasons),
            )

        if features.returns >= self.config.trend_return_threshold and features.close >= features.ema:
            reasons.extend(("positive return exceeds trend threshold", "price is at or above EMA"))
            return RegimeClassification(
                features.event_time.astimezone(timezone.utc),
                "TREND_UP",
                max(trend_score, Decimal("0.5")),
                trend_score,
                volatility_score,
                volume_score,
                tuple(reasons),
            )

        if features.returns <= -self.config.trend_return_threshold and features.close <= features.ema:
            reasons.extend(("negative return exceeds trend threshold", "price is at or below EMA"))
            return RegimeClassification(
                features.event_time.astimezone(timezone.utc),
                "TREND_DOWN",
                max(trend_score, Decimal("0.5")),
                trend_score,
                volatility_score,
                volume_score,
                tuple(reasons),
            )

        reasons.append("no directional trend threshold satisfied")
        return RegimeClassification(
            features.event_time.astimezone(timezone.utc),
            "RANGE",
            max(Decimal("0.5"), Decimal("1") - trend_score),
            trend_score,
            volatility_score,
            volume_score,
            tuple(reasons),
        )

    def classify_series(self, features: list[TechnicalFeatures]) -> list[RegimeClassification]:
        """Classify each feature row in caller-supplied order without future data."""
        previous: datetime | None = None
        for item in features:
            timestamp = item.event_time.astimezone(timezone.utc)
            if previous is not None and timestamp <= previous:
                raise ValueError("feature timestamps must be strictly increasing")
            previous = timestamp
        return [self.classify(item) for item in features]

    def _trend_score(self, features: TechnicalFeatures) -> Decimal:
        if features.returns is None:
            return Decimal("0")
        magnitude = abs(features.returns) / self.config.trend_return_threshold
        return min(Decimal("1"), magnitude)

    def _volatility_score(self, features: TechnicalFeatures) -> Decimal:
        if features.range_pct is None:
            return Decimal("0")
        return min(Decimal("1"), features.range_pct / self.config.volatility_range_threshold)

    def _volume_score(self, features: TechnicalFeatures) -> Decimal:
        if features.volume_sma is None or features.volume_sma <= 0:
            return Decimal("0")
        # volume_sma is not directly a ratio, so this component intentionally
        # remains neutral until a point-in-time volume ratio feature is added.
        return Decimal("0")
