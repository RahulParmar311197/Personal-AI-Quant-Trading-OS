from datetime import datetime, timedelta, timezone

import pytest

from app.market_data.live import LiveEventGuard, LiveMarketDataEvent, LiveDataProvider


UTC = timezone.utc


def event(**overrides: object) -> LiveMarketDataEvent:
    values: dict[str, object] = {
        "instrument_id": "NSE:NIFTY50",
        "exchange": "NSE",
        "segment": "INDEX",
        "symbol": "NIFTY50",
        "provider": "test",
        "provider_event_id": "evt-1",
        "event_time": datetime(2026, 9, 12, 9, 15, tzinfo=UTC),
        "ingested_at": datetime(2026, 9, 12, 9, 15, 1, tzinfo=UTC),
        "payload": {"last_price": 25000},
    }
    values.update(overrides)
    return LiveMarketDataEvent(**values)


def test_live_event_requires_timezone_aware_timestamps() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        event(event_time=datetime(2026, 9, 12, 9, 15))


def test_guard_deduplicates_provider_event_id() -> None:
    guard = LiveEventGuard()
    first = guard.accept(event(), now=datetime(2026, 9, 12, 9, 15, 1, tzinfo=UTC))
    second = guard.accept(event(), now=datetime(2026, 9, 12, 9, 15, 1, tzinfo=UTC))
    assert first is not None
    assert second is None


def test_guard_rejects_out_of_order_sequence() -> None:
    guard = LiveEventGuard()
    assert guard.accept(event(provider_event_id="a", sequence=10), now=datetime(2026, 9, 12, 9, 15, tzinfo=UTC))
    assert guard.accept(event(provider_event_id="b", sequence=9), now=datetime(2026, 9, 12, 9, 15, tzinfo=UTC)) is None


def test_guard_marks_old_valid_event_stale() -> None:
    guard = LiveEventGuard(stale_after_seconds=5)
    now = datetime(2026, 9, 12, 9, 15, 20, tzinfo=UTC)
    old = event(provider_event_id="old", event_time=datetime(2026, 9, 12, 9, 15, 10, tzinfo=UTC), ingested_at=now)
    accepted = guard.accept(old, now=now)
    assert accepted is not None
    assert accepted.quality == "STALE"


def test_guard_rejects_future_event() -> None:
    guard = LiveEventGuard()
    with pytest.raises(ValueError, match="future"):
        guard.accept(event(event_time=datetime.now(UTC) + timedelta(seconds=2), ingested_at=datetime.now(UTC) + timedelta(seconds=3)))


def test_provider_contract_is_abstract() -> None:
    with pytest.raises(TypeError):
        LiveDataProvider()  # type: ignore[abstract]
