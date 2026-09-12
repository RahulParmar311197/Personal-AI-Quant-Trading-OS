"""Deterministic SMC/ICT-style market-structure features.

These definitions are intentionally explicit and versionable. They are
research features, not trade recommendations or execution instructions.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from app.market_data.contracts import HistoricalBar
from app.market_data.structure import SwingPoint

LiquiditySide = Literal["BUY_SIDE", "SELL_SIDE"]
GapDirection = Literal["BULLISH", "BEARISH"]


@dataclass(frozen=True)
class LiquidityPool:
    instrument_id: str
    side: LiquiditySide
    price: Decimal
    first_time: datetime
    second_time: datetime
    tolerance: Decimal


@dataclass(frozen=True)
class FairValueGap:
    instrument_id: str
    direction: GapDirection
    event_time: datetime
    lower: Decimal
    upper: Decimal
    reference_start: datetime
    reference_end: datetime


@dataclass(frozen=True)
class OrderBlock:
    instrument_id: str
    direction: GapDirection
    event_time: datetime
    lower: Decimal
    upper: Decimal
    displacement_time: datetime


@dataclass(frozen=True)
class PremiumDiscount:
    instrument_id: str
    event_time: datetime
    equilibrium: Decimal
    range_high: Decimal
    range_low: Decimal
    zone: Literal["PREMIUM", "DISCOUNT", "EQUILIBRIUM"]


def detect_equal_liquidity(
    bars: list[HistoricalBar],
    *,
    tolerance: Decimal = Decimal("0.0005"),
) -> list[LiquidityPool]:
    """Detect equal highs/lows from consecutive same-kind confirmed swings.

    A high is compared with the previous confirmed high, and a low with the
    previous confirmed low. Interleaved opposite-kind swings do not prevent
    detection because liquidity pools are defined within the same swing kind.
    Tolerance is relative to price: |a-b| / max(|a|,|b|) <= tolerance.
    """
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative")
    swings = _confirmed_swings(bars)
    pools: list[LiquidityPool] = []
    previous_by_kind: dict[str, SwingPoint] = {}
    for swing in swings:
        left = previous_by_kind.get(swing.kind)
        previous_by_kind[swing.kind] = swing
        if left is None:
            continue
        denominator = max(abs(left.price), abs(swing.price), Decimal("1e-18"))
        relative = abs(left.price - swing.price) / denominator
        if relative > tolerance:
            continue
        side: LiquiditySide = "BUY_SIDE" if swing.kind == "HIGH" else "SELL_SIDE"
        pools.append(
            LiquidityPool(
                instrument_id=left.instrument_id,
                side=side,
                price=(left.price + swing.price) / Decimal(2),
                first_time=left.event_time,
                second_time=swing.event_time,
                tolerance=tolerance,
            )
        )
    return pools


def detect_fair_value_gaps(bars: list[HistoricalBar]) -> list[FairValueGap]:
    """Detect three-candle imbalances using wick-to-wick non-overlap."""
    ordered = _validate_bars(bars)
    gaps: list[FairValueGap] = []
    for i in range(2, len(ordered)):
        first, middle, third = ordered[i - 2], ordered[i - 1], ordered[i]
        if third.low > first.high:
            gaps.append(
                FairValueGap(
                    instrument_id=middle.instrument_id,
                    direction="BULLISH",
                    event_time=third.event_time.astimezone(timezone.utc),
                    lower=first.high,
                    upper=third.low,
                    reference_start=first.event_time.astimezone(timezone.utc),
                    reference_end=third.event_time.astimezone(timezone.utc),
                )
            )
        if third.high < first.low:
            gaps.append(
                FairValueGap(
                    instrument_id=middle.instrument_id,
                    direction="BEARISH",
                    event_time=third.event_time.astimezone(timezone.utc),
                    lower=third.high,
                    upper=first.low,
                    reference_start=first.event_time.astimezone(timezone.utc),
                    reference_end=third.event_time.astimezone(timezone.utc),
                )
            )
    return gaps


def detect_order_blocks(
    bars: list[HistoricalBar],
    *,
    displacement_factor: Decimal = Decimal("1.5"),
    range_period: int = 10,
) -> list[OrderBlock]:
    """Detect a simple, deterministic last-opposite-candle displacement model.

    A bullish block is the final bearish candle immediately before a bullish
    displacement candle. A bearish block is the symmetric case. Displacement
    requires the candle range to exceed the trailing average range multiplied
    by `displacement_factor`. This is an explicit research definition, not a
    claim that it is the canonical interpretation of ICT/SMC terminology.
    """
    if displacement_factor <= 0 or range_period <= 0:
        raise ValueError("displacement_factor and range_period must be positive")
    ordered = _validate_bars(bars)
    blocks: list[OrderBlock] = []
    for i in range(range_period + 1, len(ordered)):
        previous = ordered[i - 1]
        current = ordered[i]
        trailing = ordered[i - range_period - 1 : i]
        average_range = sum((b.high - b.low for b in trailing), Decimal(0)) / Decimal(len(trailing))
        current_range = current.high - current.low
        if current_range <= average_range * displacement_factor:
            continue
        if current.close > current.open and previous.close < previous.open:
            blocks.append(
                OrderBlock(previous.instrument_id, "BULLISH", previous.event_time.astimezone(timezone.utc), previous.low, previous.high, current.event_time.astimezone(timezone.utc))
            )
        elif current.close < current.open and previous.close > previous.open:
            blocks.append(
                OrderBlock(previous.instrument_id, "BEARISH", previous.event_time.astimezone(timezone.utc), previous.low, previous.high, current.event_time.astimezone(timezone.utc))
            )
    return blocks


def premium_discount(
    bars: list[HistoricalBar],
    *,
    lookback: int = 20,
) -> PremiumDiscount | None:
    """Classify current close against the midpoint of a trailing price range."""
    if lookback <= 0:
        raise ValueError("lookback must be positive")
    ordered = _validate_bars(bars)
    if len(ordered) < lookback:
        return None
    window = ordered[-lookback:]
    high = max(b.high for b in window)
    low = min(b.low for b in window)
    equilibrium = (high + low) / Decimal(2)
    close = window[-1].close
    zone: Literal["PREMIUM", "DISCOUNT", "EQUILIBRIUM"]
    if close > equilibrium:
        zone = "PREMIUM"
    elif close < equilibrium:
        zone = "DISCOUNT"
    else:
        zone = "EQUILIBRIUM"
    return PremiumDiscount(window[-1].instrument_id, window[-1].event_time.astimezone(timezone.utc), equilibrium, high, low, zone)


def _confirmed_swings(bars: list[HistoricalBar]) -> list[SwingPoint]:
    from app.market_data.structure import detect_swings
    return detect_swings(bars, left_bars=1, right_bars=1)


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
