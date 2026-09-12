from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

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


def test_strategy_factory_receives_only_each_window_training_data() -> None:
    bars = [bar(i, str(100 + i)) for i in range(12)]
    seen_training_ranges: list[tuple[datetime, datetime]] = []

    def factory(training):
        assert training
        seen_training_ranges.append((training[0].event_time, training[-1].event_time))
        training_end = training[-1].event_time

        def strategy(observation, current):
            assert current.event_time >= training_end
            return None

        return strategy

    result = WalkForwardValidator().run(bars, factory, train_size=4, test_size=4)
    assert len(result.results) == 2
    assert seen_training_ranges == [
        (bars[0].event_time, bars[3].event_time),
        (bars[4].event_time, bars[7].event_time),
    ]
