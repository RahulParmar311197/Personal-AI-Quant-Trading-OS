from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.decision.engine import DecisionConfig, DecisionEngine
from app.regime.engine import RegimeClassification
from app.strategies.base import StrategySignal

UTC = timezone.utc
NOW = datetime(2026, 1, 1, 9, 20, tzinfo=UTC)


def regime(name: str, confidence: str = "0.8") -> RegimeClassification:
    return RegimeClassification(NOW, name, Decimal(confidence), Decimal("0.8"), Decimal("0.2"),
                                Decimal("0"), (f"regime={name}",))


def signal(side: str, confidence: str = "0.9") -> StrategySignal:
    return StrategySignal(NOW, side, Decimal(confidence), ("structure confirmation",))


def test_long_decision_requires_threshold_and_aligned_regime() -> None:
    result = DecisionEngine().decide(signal("LONG"), regime("TREND_UP"),
                                     ai_long_probability=Decimal("0.8"))
    assert result.action == "LONG"
    assert result.score >= Decimal("0.60")


def test_opposite_regime_can_block_trade() -> None:
    result = DecisionEngine().decide(signal("LONG"), regime("TREND_DOWN"),
                                     ai_long_probability=Decimal("0.2"))
    assert result.action == "NO_TRADE"


def test_unknown_regime_never_trades() -> None:
    result = DecisionEngine().decide(signal("LONG"), regime("UNKNOWN"),
                                     ai_long_probability=Decimal("0.99"))
    assert result.action == "NO_TRADE"


def test_high_volatility_is_blocked_by_default() -> None:
    result = DecisionEngine().decide(signal("LONG"), regime("HIGH_VOLATILITY"),
                                     ai_long_probability=Decimal("0.99"))
    assert result.action == "NO_TRADE"
    assert "high-volatility trading is disabled" in result.reasons


def test_high_volatility_can_be_explicitly_enabled() -> None:
    engine = DecisionEngine(DecisionConfig(allow_high_volatility=True))
    result = engine.decide(signal("LONG"), regime("HIGH_VOLATILITY"),
                           ai_long_probability=Decimal("0.99"))
    assert result.action == "NO_TRADE"
    assert "aggregate score below decision threshold" in result.reasons


def test_flat_and_missing_signal_do_not_trade() -> None:
    engine = DecisionEngine()
    assert engine.decide(None, regime("TREND_UP")).action == "NO_TRADE"
    assert engine.decide(signal("FLAT"), regime("TREND_UP")).action == "NO_TRADE"


def test_low_strategy_confidence_does_not_trade() -> None:
    result = DecisionEngine().decide(signal("LONG", "0.49"), regime("TREND_UP"))
    assert result.action == "NO_TRADE"


def test_future_strategy_signal_is_rejected() -> None:
    future = StrategySignal(
        datetime(2026, 1, 1, 9, 21, tzinfo=UTC), "LONG", Decimal("0.9"), ("future",)
    )
    with pytest.raises(ValueError, match="future data"):
        DecisionEngine().decide(future, regime("TREND_UP"))


def test_ai_probability_is_validated() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        DecisionEngine().decide(signal("LONG"), regime("TREND_UP"),
                                 ai_long_probability=Decimal("1.1"))


def test_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sum to 1"):
        DecisionConfig(strategy_weight=Decimal("0.5"), regime_weight=Decimal("0.2"),
                       ai_weight=Decimal("0.2"))
