"""Deterministic technical-analysis feature calculations.

The engine is deliberately pure: no provider, strategy, order, or ML behavior
is embedded here. Features are calculated only from bars at or before the
current bar, preserving point-in-time semantics.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from math import sqrt
from typing import Iterable

from app.market_data.contracts import HistoricalBar


@dataclass(frozen=True)
class TechnicalFeatures:
    event_time: datetime
    instrument_id: str
    close: Decimal
    sma: Decimal | None
    ema: Decimal | None
    rsi: Decimal | None
    atr: Decimal | None
    macd: Decimal | None
    macd_signal: Decimal | None
    bollinger_mid: Decimal | None
    bollinger_upper: Decimal | None
    bollinger_lower: Decimal | None
    volume_sma: Decimal | None
    returns: Decimal | None
    range_pct: Decimal | None
    body_pct: Decimal | None
    upper_wick_pct: Decimal | None
    lower_wick_pct: Decimal | None


def _validate_bars(bars: Iterable[HistoricalBar]) -> list[HistoricalBar]:
    ordered = sorted(bars, key=lambda b: b.event_time)
    if not ordered:
        return []
    previous: datetime | None = None
    for bar in ordered:
        if bar.event_time.tzinfo is None:
            raise ValueError("bar timestamps must be timezone-aware")
        timestamp = bar.event_time.astimezone(timezone.utc)
        if previous is not None and timestamp <= previous:
            raise ValueError("bars must have strictly increasing timestamps")
        previous = timestamp
    return ordered


def _sma(values: list[Decimal], period: int) -> Decimal | None:
    if len(values) < period:
        return None
    return sum(values[-period:], Decimal(0)) / Decimal(period)


def _ema(values: list[Decimal], period: int) -> Decimal | None:
    if len(values) < period:
        return None
    ema = sum(values[:period], Decimal(0)) / Decimal(period)
    multiplier = Decimal(2) / Decimal(period + 1)
    for value in values[period:]:
        ema = (value - ema) * multiplier + ema
    return ema


def _rsi(values: list[Decimal], period: int) -> Decimal | None:
    if len(values) < period + 1:
        return None
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    window = changes[-period:]
    gains = sum((x for x in window if x > 0), Decimal(0)) / Decimal(period)
    losses = sum((-x for x in window if x < 0), Decimal(0)) / Decimal(period)
    if losses == 0:
        return Decimal(100) if gains > 0 else Decimal(50)
    rs = gains / losses
    return Decimal(100) - (Decimal(100) / (Decimal(1) + rs))


def _atr(bars: list[HistoricalBar], period: int) -> Decimal | None:
    if len(bars) < period + 1:
        return None
    true_ranges: list[Decimal] = []
    for current, previous in zip(bars[1:], bars[:-1]):
        true_ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    return sum(true_ranges[-period:], Decimal(0)) / Decimal(period)


def _stddev(values: list[Decimal]) -> Decimal:
    mean = sum(values, Decimal(0)) / Decimal(len(values))
    variance = sum((x - mean) ** 2 for x in values) / Decimal(len(values))
    return Decimal(str(sqrt(float(variance))))


def calculate_features(
    bars: Iterable[HistoricalBar],
    *,
    sma_period: int = 20,
    ema_period: int = 20,
    rsi_period: int = 14,
    atr_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    bollinger_period: int = 20,
    bollinger_stddev: Decimal = Decimal("2"),
    volume_period: int = 20,
) -> list[TechnicalFeatures]:
    """Return one point-in-time feature record per input bar.

    Each row is calculated from the prefix ending at that row only. Warm-up
    values are represented as None rather than backfilled with future data.
    """
    if min(sma_period, ema_period, rsi_period, atr_period, macd_fast, macd_slow,
           macd_signal, bollinger_period, volume_period) <= 0:
        raise ValueError("all indicator periods must be positive")
    if macd_fast >= macd_slow:
        raise ValueError("macd_fast must be smaller than macd_slow")

    ordered = _validate_bars(bars)
    closes: list[Decimal] = []
    volumes: list[Decimal] = []
    output: list[TechnicalFeatures] = []

    for index, bar in enumerate(ordered):
        closes.append(bar.close)
        volumes.append(Decimal(bar.volume))
        previous_close = closes[-2] if len(closes) >= 2 else None
        returns = None if previous_close in (None, Decimal(0)) else (bar.close / previous_close) - Decimal(1)
        candle_range = bar.high - bar.low
        range_pct = None if bar.close == 0 else candle_range / bar.close
        body_pct = None if bar.close == 0 else abs(bar.close - bar.open) / bar.close
        upper_wick = bar.high - max(bar.open, bar.close)
        lower_wick = min(bar.open, bar.close) - bar.low
        upper_wick_pct = None if bar.close == 0 else upper_wick / bar.close
        lower_wick_pct = None if bar.close == 0 else lower_wick / bar.close

        bb_mid = _sma(closes, bollinger_period)
        bb_upper = bb_lower = None
        if len(closes) >= bollinger_period and bb_mid is not None:
            deviation = _stddev(closes[-bollinger_period:])
            bb_upper = bb_mid + bollinger_stddev * deviation
            bb_lower = bb_mid - bollinger_stddev * deviation

        fast = _ema(closes, macd_fast)
        slow = _ema(closes, macd_slow)
        macd_value = None if fast is None or slow is None else fast - slow
        macd_history = []
        if macd_value is not None:
            for end in range(macd_slow, len(closes) + 1):
                fast_value = _ema(closes[:end], macd_fast)
                slow_value = _ema(closes[:end], macd_slow)
                if fast_value is not None and slow_value is not None:
                    macd_history.append(fast_value - slow_value)
        macd_signal_value = _ema(macd_history, macd_signal)

        output.append(
            TechnicalFeatures(
                event_time=bar.event_time.astimezone(timezone.utc),
                instrument_id=bar.instrument_id,
                close=bar.close,
                sma=_sma(closes, sma_period),
                ema=_ema(closes, ema_period),
                rsi=_rsi(closes, rsi_period),
                atr=_atr(ordered[: index + 1], atr_period),
                macd=macd_value,
                macd_signal=macd_signal_value,
                bollinger_mid=bb_mid,
                bollinger_upper=bb_upper,
                bollinger_lower=bb_lower,
                volume_sma=_sma(volumes, volume_period),
                returns=returns,
                range_pct=range_pct,
                body_pct=body_pct,
                upper_wick_pct=upper_wick_pct,
                lower_wick_pct=lower_wick_pct,
            )
        )
    return output
