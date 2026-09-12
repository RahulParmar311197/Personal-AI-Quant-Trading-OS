from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.market_data.contracts import HistoricalBar
from app.strategies.base import Strategy, StrategyContext, StrategyMetadata, StrategySignal
from app.strategies.registry import StrategyRegistry


UTC = timezone.utc


def bar(minute: int) -> HistoricalBar:
    value = Decimal("100") + minute
    return HistoricalBar(
        instrument_id="NSE:NIFTY",
        timeframe="1m",
        event_time=datetime(2026, 1, 1, 9, 15 + minute, tzinfo=UTC),
        open=value,
        high=value + 1,
        low=value - 1,
        close=value + Decimal("0.5"),
        volume=1000,
        source="test",
    )


class TestStrategy(Strategy):
    metadata = StrategyMetadata("test-strategy", "1.0.0", "deterministic test strategy")

    def evaluate(self, context: StrategyContext) -> StrategySignal:
        return StrategySignal(
            event_time=context.as_of,
            side="LONG",
            confidence=Decimal("0.75"),
            evidence=("test evidence",),
        )


def test_registry_register_get_and_list() -> None:
    strategy = TestStrategy()
    registry = StrategyRegistry([strategy])

    assert registry.get("test-strategy", "1.0.0") is strategy
    assert registry.get("test-strategy") is strategy
    assert registry.list_metadata() == (strategy.metadata,)
    assert len(registry) == 1


def test_registry_rejects_duplicate_identity() -> None:
    registry = StrategyRegistry([TestStrategy()])

    with pytest.raises(ValueError, match="already registered"):
        registry.register(TestStrategy())


def test_registry_requires_version_when_multiple_versions_exist() -> None:
    class V2(TestStrategy):
        metadata = StrategyMetadata("test-strategy", "2.0.0")

    registry = StrategyRegistry([TestStrategy(), V2()])

    with pytest.raises(ValueError, match="version is required"):
        registry.get("test-strategy")
    assert registry.get("test-strategy", "2.0.0").metadata.version == "2.0.0"


def test_registry_rejects_unknown_strategy() -> None:
    with pytest.raises(KeyError, match="unknown strategy"):
        StrategyRegistry().get("missing")


def test_context_rejects_future_bars() -> None:
    with pytest.raises(ValueError, match="future bars"):
        StrategyContext(
            as_of=datetime(2026, 1, 1, 9, 16, tzinfo=UTC),
            bars=(bar(0), bar(2)),
        )


def test_context_is_point_in_time_and_features_are_read_only() -> None:
    features = {"rsi": Decimal("55")}
    context = StrategyContext(
        as_of=bar(1).event_time,
        bars=(bar(0), bar(1)),
        features=features,
    )

    features["rsi"] = Decimal("10")
    assert context.features["rsi"] == Decimal("55")
    with pytest.raises(TypeError):
        context.features["rsi"] = Decimal("10")  # type: ignore[index]


def test_signal_validates_confidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        StrategySignal(
            event_time=bar(0).event_time,
            side="LONG",
            confidence=Decimal("1.01"),
        )
