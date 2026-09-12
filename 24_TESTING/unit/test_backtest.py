from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.backtest.engine import BacktestConfig, BacktestEngine, Signal
from app.market_data.contracts import HistoricalBar

UTC = timezone.utc
BASE = datetime(2026, 9, 12, 9, 15, tzinfo=UTC)


def bar(i: int, open_: int, close: int) -> HistoricalBar:
    return HistoricalBar(
        instrument_id="NSE:NIFTY50", timeframe="5m",
        event_time=BASE + timedelta(minutes=5 * i),
        open=Decimal(open_), high=Decimal(max(open_, close) + 1),
        low=Decimal(min(open_, close) - 1), close=Decimal(close), volume=100,
        source="test", is_final=True,
    )


def test_signal_executes_on_next_bar_open() -> None:
    engine = BacktestEngine(BacktestConfig(initial_capital=Decimal("100000")))
    bars = [bar(0, 100, 105), bar(1, 110, 112), bar(2, 120, 121)]

    def signal_fn(history, current):
        return Signal(event_time=current.event_time, side="LONG", quantity=Decimal("1")) if current is bars[0] else None

    result = engine.run(bars, signal_fn)
    assert result.fills[0].event_time == bars[1].event_time
    assert result.fills[0].price == Decimal("110")


def test_fee_and_slippage_reduce_profit() -> None:
    engine = BacktestEngine(BacktestConfig(
        initial_capital=Decimal("100000"), fee_bps=Decimal("10"), slippage_bps=Decimal("10")
    ))
    bars = [bar(0, 100, 100), bar(1, 110, 110), bar(2, 120, 120), bar(3, 120, 120)]

    def signal_fn(history, current):
        if current is bars[0]:
            return Signal(event_time=current.event_time, side="LONG", quantity=Decimal("1"))
        if current is bars[2]:
            return Signal(event_time=current.event_time, side="SHORT", quantity=Decimal("1"))
        return None

    result = engine.run(bars, signal_fn)
    assert len(result.trades) == 1
    assert result.trades[0].net_pnl < result.trades[0].gross_pnl


def test_future_signal_is_rejected() -> None:
    engine = BacktestEngine()
    bars = [bar(0, 100, 100), bar(1, 101, 101)]

    def signal_fn(history, current):
        return Signal(event_time=bars[1].event_time, side="LONG", quantity=Decimal("1"))

    with pytest.raises(ValueError, match="future data"):
        engine.run(bars, signal_fn)
