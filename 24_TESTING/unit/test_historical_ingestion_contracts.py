from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.market_data.contracts import HistoricalBar, HistoricalBarRequest
from app.market_data.ingestion import HistoricalIngestionService
from app.market_data.ports import HistoricalDataProvider


UTC = timezone.utc


def request() -> HistoricalBarRequest:
    return HistoricalBarRequest(
        instrument_id="NSE:NIFTY50",
        timeframe="1m",
        start_time=datetime(2026, 1, 1, 9, 15, tzinfo=UTC),
        end_time=datetime(2026, 1, 1, 9, 18, tzinfo=UTC),
        provider="test",
        chunk_size=2,
    )


def bar(minute: int) -> HistoricalBar:
    return HistoricalBar(
        instrument_id="NSE:NIFTY50",
        timeframe="1m",
        event_time=datetime(2026, 1, 1, 9, minute, tzinfo=UTC),
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal("101"),
        volume=100,
        source="test",
    )


class Provider(HistoricalDataProvider):
    name = "test"

    def __init__(self) -> None:
        self.calls = 0

    def fetch(self, request: HistoricalBarRequest):
        self.calls += 1
        if self.calls == 1:
            return type("Result", (), {"bars": [bar(15)], "next_start_time": datetime(2026, 1, 1, 9, 16, tzinfo=UTC), "complete": False})()
        return type("Result", (), {"bars": [bar(16), bar(17)], "next_start_time": None, "complete": True})()


def test_ingestion_is_bounded_and_persists_canonical_pages() -> None:
    stored: list[HistoricalBar] = []
    provider = Provider()

    count = HistoricalIngestionService(provider, lambda bars: (stored.extend(bars), len(bars))[1]).ingest(request())

    assert count == 3
    assert provider.calls == 2
    assert [item.event_time.minute for item in stored] == [15, 16, 17]


def test_request_rejects_naive_timestamps() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        HistoricalBarRequest(
            instrument_id="NSE:NIFTY50",
            timeframe="1m",
            start_time=datetime(2026, 1, 1, 9, 15),
            end_time=datetime(2026, 1, 1, 9, 18, tzinfo=UTC),
            provider="test",
        )


def test_bar_rejects_invalid_ohlc() -> None:
    with pytest.raises(ValueError, match="high must contain"):
        HistoricalBar(
            instrument_id="NSE:NIFTY50",
            timeframe="1m",
            event_time=datetime(2026, 1, 1, 9, 15, tzinfo=UTC),
            open=Decimal("103"),
            high=Decimal("102"),
            low=Decimal("99"),
            close=Decimal("101"),
            volume=100,
            source="test",
        )
