from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.market_data.contracts import HistoricalBar
from app.market_data.structure import classify_structure, detect_structure_breaks, detect_swings

UTC = timezone.utc


def bar(i: int, high: int, low: int, close: int) -> HistoricalBar:
    return HistoricalBar(
        instrument_id="NSE:NIFTY50",
        timeframe="5m",
        event_time=datetime(2026, 9, 12, 9, 15, tzinfo=UTC) + timedelta(minutes=5 * i),
        open=Decimal(close),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=100,
        source="test",
        is_final=True,
    )


def test_swing_high_requires_right_side_confirmation() -> None:
    bars = [bar(0, 100, 90, 95), bar(1, 110, 91, 105), bar(2, 120, 100, 115),
            bar(3, 110, 95, 105), bar(4, 108, 94, 100)]
    swings = detect_swings(bars, left_bars=1, right_bars=1)
    highs = [s for s in swings if s.kind == "HIGH"]
    assert len(highs) == 1
    assert highs[0].event_time == bars[2].event_time


def test_structure_classification_distinguishes_higher_and_lower_swings() -> None:
    bars = [bar(0, 100, 90, 95), bar(1, 110, 91, 105), bar(2, 120, 100, 115),
            bar(3, 108, 94, 100), bar(4, 112, 96, 105), bar(5, 100, 88, 92),
            bar(6, 105, 90, 100)]
    swings = detect_swings(bars, left_bars=1, right_bars=1)
    events = classify_structure(swings)
    labels = [event.label for event in events if event.label is not None]
    assert "HH" in labels or "LH" in labels
    assert "HL" in labels or "LL" in labels


def test_break_requires_close_beyond_confirmed_level() -> None:
    bars = [bar(0, 100, 90, 95), bar(1, 110, 91, 105), bar(2, 100, 92, 96),
            bar(3, 112, 93, 111), bar(4, 115, 94, 114)]
    swings = detect_swings(bars, left_bars=1, right_bars=1)
    breaks = detect_structure_breaks(bars, swings)
    bullish = [event for event in breaks if event.direction == "BULLISH"]
    assert bullish
    assert bullish[0].break_kind == "BOS"
    assert bullish[0].reference_price == Decimal("110")


def test_future_bars_can_only_add_later_confirmed_events() -> None:
    bars = [bar(0, 100, 90, 95), bar(1, 110, 91, 105), bar(2, 120, 100, 115),
            bar(3, 110, 95, 105), bar(4, 108, 94, 100), bar(5, 130, 90, 125)]
    early = detect_swings(bars[:5], left_bars=1, right_bars=1)
    full = detect_swings(bars, left_bars=1, right_bars=1)
    assert {(s.event_time, s.kind, s.price) for s in early} <= {(s.event_time, s.kind, s.price) for s in full}
