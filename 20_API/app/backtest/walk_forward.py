"""Rolling walk-forward validation for deterministic strategy research."""

from dataclasses import dataclass
from typing import Callable, Sequence

from app.backtest.engine import BacktestEngine, BacktestResult, Signal
from app.market_data.contracts import HistoricalBar


@dataclass(frozen=True)
class WalkForwardWindow:
    train_start: int
    train_end: int
    test_start: int
    test_end: int


@dataclass(frozen=True)
class WalkForwardResult:
    windows: tuple[WalkForwardWindow, ...]
    results: tuple[BacktestResult, ...]


def build_windows(
    bar_count: int,
    *,
    train_size: int,
    test_size: int,
    step_size: int | None = None,
) -> list[WalkForwardWindow]:
    """Create chronological train/test windows with no overlap leakage."""
    if bar_count < 0:
        raise ValueError("bar_count cannot be negative")
    if train_size <= 0 or test_size <= 0:
        raise ValueError("train_size and test_size must be positive")
    step = step_size if step_size is not None else test_size
    if step <= 0:
        raise ValueError("step_size must be positive")

    windows: list[WalkForwardWindow] = []
    start = 0
    while start + train_size + test_size <= bar_count:
        train_end = start + train_size
        test_end = train_end + test_size
        windows.append(WalkForwardWindow(start, train_end, train_end, test_end))
        start += step
    return windows


class WalkForwardValidator:
    """Run fixed strategy factories on sequential out-of-sample windows.

    The V1 contract does not optimize parameters itself. A caller may use the
    training slice to construct a strategy, but the resulting strategy is then
    evaluated only on the subsequent test slice.
    """

    def __init__(self, engine: BacktestEngine | None = None) -> None:
        self.engine = engine or BacktestEngine()

    def run(
        self,
        bars: Sequence[HistoricalBar],
        strategy_factory: Callable[[Sequence[HistoricalBar]], Callable[[list[HistoricalBar], HistoricalBar], Signal | None]],
        *,
        train_size: int,
        test_size: int,
        step_size: int | None = None,
    ) -> WalkForwardResult:
        windows = build_windows(
            len(bars), train_size=train_size, test_size=test_size, step_size=step_size
        )
        results: list[BacktestResult] = []
        for window in windows:
            training = bars[window.train_start : window.train_end]
            testing = bars[window.test_start : window.test_end]
            strategy = strategy_factory(training)
            results.append(self.engine.run(list(testing), strategy))
        return WalkForwardResult(tuple(windows), tuple(results))
