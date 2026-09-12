"""Deterministic market-structure analysis from OHLCV bars."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from app.market_data.contracts import HistoricalBar

SwingKind = Literal["HIGH", "LOW"]
StructureLabel = Literal["HH", "HL", "LH", "LL"]
BreakKind = Literal["BOS", "CHOCH"]


@dataclass(frozen=True)
class SwingPoint:
    instrument_id: str
    event_time: datetime
    price: Decimal
    kind: SwingKind
    left_bars: int
    right_bars: int


@dataclass(frozen=True)
class StructureEvent:
    instrument_id: str
    event_time: datetime
    label: StructureLabel | None
    break_kind: BreakKind | None
    direction: Literal["BULLISH", "BEARISH"] | None
    reference_time: datetime | None
    reference_price: Decimal | None


def detect_swings(bars: list[HistoricalBar], *, left_bars: int = 2, right_bars: int = 2) -> list[SwingPoint]:
    """Detect confirmed local swing highs/lows using a symmetric window.

    A swing at index i is only emitted after the `right_bars` candles to its
    right exist. Therefore it is a confirmed historical event, not a forecast.
    Ties are rejected to keep the definition deterministic.
    """
    if left_bars < 1 or right_bars < 1:
        raise ValueError("left_bars and right_bars must be positive")
    ordered = _validate_bars(bars)
    swings: list[SwingPoint] = []
    for i in range(left_bars, len(ordered) - right_bars):
        current = ordered[i]
        window = ordered[i - left_bars : i + right_bars + 1]
        highs = [bar.high for bar in window]
        lows = [bar.low for bar in window]
        if current.high == max(highs) and highs.count(current.high) == 1:
            swings.append(_swing(current, "HIGH", left_bars, right_bars, current.high))
        if current.low == min(lows) and lows.count(current.low) == 1:
            swings.append(_swing(current, "LOW", left_bars, right_bars, current.low))
    return swings


def classify_structure(swings: list[SwingPoint]) -> list[StructureEvent]:
    """Classify successive same-kind swings as HH/HL/LH/LL."""
    previous: dict[SwingKind, SwingPoint] = {}
    events: list[StructureEvent] = []
    for swing in sorted(swings, key=lambda item: (item.event_time, item.kind)):
        prior = previous.get(swing.kind)
        if prior is None:
            label = None
        elif swing.kind == "HIGH":
            label = "HH" if swing.price > prior.price else "LH"
        else:
            label = "HL" if swing.price > prior.price else "LL"
        events.append(
            StructureEvent(
                instrument_id=swing.instrument_id,
                event_time=swing.event_time,
                label=label,
                break_kind=None,
                direction=None,
                reference_time=prior.event_time if prior else None,
                reference_price=prior.price if prior else None,
            )
        )
        previous[swing.kind] = swing
    return events


def detect_structure_breaks(bars: list[HistoricalBar], swings: list[SwingPoint]) -> list[StructureEvent]:
    """Emit deterministic BOS/CHOCH events when a close crosses a confirmed swing.

    Only swings confirmed before the breaking bar are eligible. A close equal
    to the level is not considered a break. The previous break direction is
    used to distinguish continuation (BOS) from directional change (CHOCH).
    """
    ordered = _validate_bars(bars)
    confirmed = sorted(swings, key=lambda item: item.event_time)
    last_broken_high: datetime | None = None
    last_broken_low: datetime | None = None
    direction: Literal["BULLISH", "BEARISH"] | None = None
    events: list[StructureEvent] = []
    for bar in ordered:
        eligible_highs = [s for s in confirmed if s.kind == "HIGH" and s.event_time < bar.event_time]
        eligible_lows = [s for s in confirmed if s.kind == "LOW" and s.event_time < bar.event_time]
        high = max(eligible_highs, key=lambda s: s.event_time) if eligible_highs else None
        low = max(eligible_lows, key=lambda s: s.event_time) if eligible_lows else None
        if high and high.event_time != last_broken_high and bar.close > high.price:
            new_direction: Literal["BULLISH", "BEARISH"] = "BULLISH"
            kind: BreakKind = "BOS" if direction in (None, "BULLISH") else "CHOCH"
            events.append(_break(bar, kind, new_direction, high))
            direction = new_direction
            last_broken_high = high.event_time
        if low and low.event_time != last_broken_low and bar.close < low.price:
            new_direction = "BEARISH"
            kind = "BOS" if direction in (None, "BEARISH") else "CHOCH"
            events.append(_break(bar, kind, new_direction, low))
            direction = new_direction
            last_broken_low = low.event_time
    return events


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


def _swing(bar: HistoricalBar, kind: SwingKind, left: int, right: int, price: Decimal) -> SwingPoint:
    return SwingPoint(bar.instrument_id, bar.event_time.astimezone(timezone.utc), price, kind, left, right)


def _break(bar: HistoricalBar, kind: BreakKind, direction: Literal["BULLISH", "BEARISH"], swing: SwingPoint) -> StructureEvent:
    return StructureEvent(
        instrument_id=bar.instrument_id,
        event_time=bar.event_time.astimezone(timezone.utc),
        label=None,
        break_kind=kind,
        direction=direction,
        reference_time=swing.event_time,
        reference_price=swing.price,
    )
