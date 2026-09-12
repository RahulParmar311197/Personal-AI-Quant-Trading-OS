"""Minimal deterministic event-driven backtest engine.

Signals are observations at a bar close. Orders execute no earlier than the
next bar open, preventing the common close-to-close look-ahead error.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Literal

from app.market_data.contracts import HistoricalBar

Side = Literal["LONG", "SHORT"]


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: Decimal = Decimal("100000")
    risk_per_trade: Decimal = Decimal("0.01")
    fee_bps: Decimal = Decimal("0")
    slippage_bps: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if not Decimal("0") <= self.risk_per_trade <= Decimal("1"):
            raise ValueError("risk_per_trade must be between 0 and 1")
        if self.fee_bps < 0 or self.slippage_bps < 0:
            raise ValueError("fee_bps and slippage_bps cannot be negative")


@dataclass(frozen=True)
class Signal:
    event_time: datetime
    side: Side
    quantity: Decimal
    stop_price: Decimal | None = None


@dataclass(frozen=True)
class Fill:
    event_time: datetime
    side: Side
    quantity: Decimal
    price: Decimal
    fee: Decimal


@dataclass(frozen=True)
class Trade:
    entry: Fill
    exit: Fill
    gross_pnl: Decimal
    net_pnl: Decimal


@dataclass(frozen=True)
class BacktestResult:
    initial_capital: Decimal
    final_capital: Decimal
    fills: tuple[Fill, ...]
    trades: tuple[Trade, ...]


class BacktestEngine:
    """Single-position, next-bar-open execution model for V1 research."""

    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.config = config or BacktestConfig()

    def run(
        self,
        bars: list[HistoricalBar],
        signal_fn: Callable[[list[HistoricalBar], HistoricalBar], Signal | None],
    ) -> BacktestResult:
        ordered = _validate_bars(bars)
        if len(ordered) < 2:
            return BacktestResult(self.config.initial_capital, self.config.initial_capital, (), ())

        capital = self.config.initial_capital
        fills: list[Fill] = []
        trades: list[Trade] = []
        open_position: Fill | None = None
        pending: Signal | None = None

        for index, bar in enumerate(ordered):
            if pending is not None:
                fill = self._fill(pending, bar)
                fills.append(fill)
                if open_position is None:
                    open_position = fill
                else:
                    trade = self._close_trade(open_position, fill)
                    trades.append(trade)
                    capital += trade.net_pnl
                    open_position = None
                pending = None

            if index == len(ordered) - 1:
                break

            observation = ordered[: index + 1]
            signal = signal_fn(observation, bar)
            if signal is not None:
                _validate_signal(signal, bar)
                if open_position is None:
                    pending = signal
                elif signal.side != open_position.side:
                    pending = signal

        return BacktestResult(self.config.initial_capital, capital, tuple(fills), tuple(trades))

    def _fill(self, signal: Signal, execution_bar: HistoricalBar) -> Fill:
        direction = Decimal("1") if signal.side == "LONG" else Decimal("-1")
        multiplier = Decimal("1") + direction * self.config.slippage_bps / Decimal("10000")
        price = execution_bar.open * multiplier
        fee = abs(price * signal.quantity) * self.config.fee_bps / Decimal("10000")
        return Fill(execution_bar.event_time.astimezone(timezone.utc), signal.side, signal.quantity, price, fee)

    @staticmethod
    def _close_trade(entry: Fill, exit_fill: Fill) -> Trade:
        direction = Decimal("1") if entry.side == "LONG" else Decimal("-1")
        gross = (exit_fill.price - entry.price) * entry.quantity * direction
        net = gross - entry.fee - exit_fill.fee
        return Trade(entry, exit_fill, gross, net)


def _validate_bars(bars: list[HistoricalBar]) -> list[HistoricalBar]:
    ordered = sorted(bars, key=lambda bar: bar.event_time)
    previous: datetime | None = None
    for bar in ordered:
        if bar.event_time.tzinfo is None:
            raise ValueError("bar timestamps must be timezone-aware")
        timestamp = bar.event_time.astimezone(timezone.utc)
        if previous is not None and timestamp <= previous:
            raise ValueError("bars must have strictly increasing timestamps")
        previous = timestamp
    return ordered


def _validate_signal(signal: Signal, bar: HistoricalBar) -> None:
    if signal.event_time.tzinfo is None:
        raise ValueError("signal timestamp must be timezone-aware")
    if signal.event_time.astimezone(timezone.utc) > bar.event_time.astimezone(timezone.utc):
        raise ValueError("signal cannot reference future data")
    if signal.quantity <= 0:
        raise ValueError("signal quantity must be positive")
