"""Deterministic strategy-signal decision engine.

The decision layer aggregates independent evidence into a decision proposal.
It does not size positions, approve risk, or create broker orders.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from app.regime.engine import MarketRegime, RegimeClassification
from app.strategies.base import StrategySignal

DecisionAction = Literal["LONG", "SHORT", "NO_TRADE"]


@dataclass(frozen=True)
class DecisionConfig:
    """Deterministic thresholds and weights for evidence aggregation."""

    strategy_weight: Decimal = Decimal("0.60")
    regime_weight: Decimal = Decimal("0.20")
    ai_weight: Decimal = Decimal("0.20")
    minimum_score: Decimal = Decimal("0.60")
    minimum_strategy_confidence: Decimal = Decimal("0.50")
    allow_high_volatility: bool = False

    def __post_init__(self) -> None:
        weights = (self.strategy_weight, self.regime_weight, self.ai_weight)
        if any(weight < 0 for weight in weights):
            raise ValueError("decision weights cannot be negative")
        if sum(weights, Decimal(0)) != Decimal(1):
            raise ValueError("decision weights must sum to 1")
        if not Decimal("0") <= self.minimum_score <= Decimal("1"):
            raise ValueError("minimum_score must be between 0 and 1")
        if not Decimal("0") <= self.minimum_strategy_confidence <= Decimal("1"):
            raise ValueError("minimum_strategy_confidence must be between 0 and 1")


@dataclass(frozen=True)
class DecisionResult:
    """Auditable decision proposal; not an executable order."""

    event_time: datetime
    action: DecisionAction
    score: Decimal
    strategy_score: Decimal
    regime_score: Decimal
    ai_score: Decimal
    regime: MarketRegime
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")
        for name, value in (("score", self.score), ("strategy_score", self.strategy_score),
                            ("regime_score", self.regime_score), ("ai_score", self.ai_score)):
            if not Decimal("0") <= value <= Decimal("1"):
                raise ValueError(f"{name} must be between 0 and 1")
        if any(not reason.strip() for reason in self.reasons):
            raise ValueError("reasons cannot contain empty entries")


class DecisionEngine:
    """Combine strategy, regime and optional AI evidence without execution authority."""

    def __init__(self, config: DecisionConfig | None = None) -> None:
        self.config = config or DecisionConfig()

    def decide(
        self,
        strategy_signal: StrategySignal | None,
        regime: RegimeClassification,
        *,
        ai_long_probability: Decimal | None = None,
    ) -> DecisionResult:
        event_time = regime.event_time.astimezone(timezone.utc)
        ai_score = _validate_probability(ai_long_probability, "ai_long_probability")
        if strategy_signal is None:
            return self._no_trade(event_time, regime, ai_score, "no strategy signal")
        signal_time = strategy_signal.event_time.astimezone(timezone.utc)
        if signal_time > event_time:
            raise ValueError("strategy signal cannot reference future data")
        if strategy_signal.confidence < self.config.minimum_strategy_confidence:
            return self._no_trade(event_time, regime, ai_score, "strategy confidence below minimum")
        if strategy_signal.side == "FLAT":
            return self._no_trade(event_time, regime, ai_score, "strategy explicitly requested FLAT")
        if regime.regime == "UNKNOWN":
            return self._no_trade(event_time, regime, ai_score, "market regime is UNKNOWN")
        if regime.regime == "HIGH_VOLATILITY" and not self.config.allow_high_volatility:
            return self._no_trade(event_time, regime, ai_score, "high-volatility trading is disabled")

        strategy_score = strategy_signal.confidence
        regime_score = _regime_alignment(strategy_signal.side, regime.regime)
        ai_directional_score = _ai_alignment(strategy_signal.side, ai_score)
        score = (
            self.config.strategy_weight * strategy_score
            + self.config.regime_weight * regime_score
            + self.config.ai_weight * ai_directional_score
        )
        reasons = list(strategy_signal.evidence)
        reasons.append(f"regime={regime.regime}")
        if ai_long_probability is not None:
            reasons.append(f"ai_long_probability={ai_long_probability}")
        if score < self.config.minimum_score:
            reasons.append("aggregate score below decision threshold")
            return DecisionResult(event_time, "NO_TRADE", score, strategy_score, regime_score,
                                  ai_directional_score, regime.regime, tuple(reasons))
        reasons.append("aggregate score meets decision threshold")
        return DecisionResult(event_time, strategy_signal.side, score, strategy_score, regime_score,
                              ai_directional_score, regime.regime, tuple(reasons))

    def _no_trade(self, event_time: datetime, regime: RegimeClassification, ai_score: Decimal,
                  reason: str) -> DecisionResult:
        return DecisionResult(event_time, "NO_TRADE", Decimal(0), Decimal(0), Decimal(0),
                              ai_score, regime.regime, (reason,))


def _validate_probability(value: Decimal | None, name: str) -> Decimal:
    if value is None:
        return Decimal("0.5")
    if not Decimal("0") <= value <= Decimal("1"):
        raise ValueError(f"{name} must be between 0 and 1")
    return value


def _regime_alignment(side: Literal["LONG", "SHORT", "FLAT"], regime: MarketRegime) -> Decimal:
    if side == "LONG":
        return Decimal("1") if regime == "TREND_UP" else Decimal("0.5") if regime == "RANGE" else Decimal("0")
    if side == "SHORT":
        return Decimal("1") if regime == "TREND_DOWN" else Decimal("0.5") if regime == "RANGE" else Decimal("0")
    return Decimal("0.5")


def _ai_alignment(side: Literal["LONG", "SHORT", "FLAT"], probability: Decimal) -> Decimal:
    if side == "LONG":
        return probability
    if side == "SHORT":
        return Decimal("1") - probability
    return Decimal("0.5")
