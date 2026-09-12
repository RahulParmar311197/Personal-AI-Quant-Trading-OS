from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.market_data.contracts import HistoricalBar
from app.market_data.technical import calculate_features

UTC = timezone.utc


def make_bars(count: int) -> list[HistoricalBar]:
    start = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    return [
        HistoricalBar(
            instrument_id="NSE:NIFTY50",
            timeframe="1m",
            event_time=start + timedelta(minutes=i),
            open=Decimal(100 + i),
            high=Decimal(102 + i),
            low=Decimal(99 + i),
            close=Decimal(101 + i),
            volume=1000 + i,
            source="test",
            is_final=True,
        )
        for i in range(count)
    ]


def test_warmup_values_are_none_without_lookahead() -> None:
    bars = make_bars(25)
    result = calculate_features(bars, sma_period=5, ema_period=5, rsi_period=3, atr_period=3,
                                bollinger_period=5, volume_period=5)
    assert len(result) == 25
    assert result[0].sma is None
    assert result[3].sma is None
    assert result[4].sma == Decimal("103")
    assert result[0].rsi is None


def test_feature_at_time_does_not_change_when_future_bars_are_appended() -> None:
    bars = make_bars(30)
    first = calculate_features(bars[:20], sma_period=5, ema_period=5, rsi_period=3, atr_period=3,
                                bollinger_period=5, volume_period=5)[19]
    second = calculate_features(bars, sma_period=5, ema_period=5, rsi_period=3, atr_period=3,
                                bollinger_period=5, volume_period=5)[19]
    assert first == second


def test_invalid_periods_are_rejected() -> None:
    with pytest.raises(ValueError, match="periods must be positive"):
        calculate_features(make_bars(5), sma_period=0)


def test_macd_period_order_is_validated() -> None:
    with pytest.raises(ValueError, match="macd_fast"):
        calculate_features(make_bars(30), macd_fast=20, macd_slow=10)
