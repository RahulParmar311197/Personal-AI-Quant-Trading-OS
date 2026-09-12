from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.backtest.engine import Signal
from app.backtest.walk_forward import WalkForwardValidator, build_windows
from app.market_data.contracts import HistoricalBar


def bar(index: int, close: str) -> HistoricalBar:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=index)
    value = Decimal(close)
    return HistoricalBar(
        instrument_id="NIFTY",
        timeframe="1m",
        event_time=timestamp,
        open=value,
        high=value,
        low=value,
        close=value,
        volume=1,
        source="test",
    )


def test_build_windows_are_chronological_and_non_overlapping() -> None:
    windows = build_windows(20, train_size=8, test_size=4)
    assert windows == [
        windows[0], windows[1], windows[2]
    ]
    assert [(w.train_start, w.train_end, w.test_start, w.test_end) for w in windows] == [
        (0, 8, 8, 12), (4, 12, 12, 16), (8, 16, 16, 20)
    ]
    assert all(w.train_end == w.test_start for w in windows)


def test_invalid_window_parameters_are_rejected() -> None:
    with pytest.raises(ValueError):
        build_windows(10, train_size=0, test_size=2)
    with pytest.raises(ValueError):
        build_windows(10, train_size=2, test_size=0)
    with pytest.raises(ValueError):
        build_windows(10, train_size=2, test_size=2, step_size=0)


def test_strategy_factory_receives_training_data_only() -> None:
    bars = [bar(i, str(100 + i)) for i in range(12)]
    seen_training_lengths: list[int] = []

    def factory(training):
        seen_training_lengths.append(len(training))
        assert all(item.event_time < bars[8].event_time for item in training) or len(training) == 4

        def strategy(observation, current):
            assert current.event_time >= training[-1].event_time
            return None

        return strategy

    result = WalkForwardValidator().run(bars, factory, train_size=4, test_size=4)
    assert len(result.results) == 1
    assert seen_training_lengths == [4]
