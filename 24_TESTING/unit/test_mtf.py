from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.market_data.contracts import HistoricalBar
from app.market_data.mtf import aggregate_bars, bucket_start

UTC = timezone.utc


def make_bar(minute: int, *, final: bool = True, close: str = "101") -> HistoricalBar:
    return HistoricalBar(
        instrument_id="NSE:NIFTY50",
        timeframe="1m",
        event_time=datetime(2026, 9, 12, 9, minute, tzinfo=UTC),
        open=Decimal("100"),
        high=Decimal("102") + minute,
        low=Decimal("99"),
        close=Decimal(close),
        volume=100 + minute,
        source="test",
        is_final=final,
    )


def test_bucket_start_is_epoch_aligned() -> None:
    value = bucket_start(datetime(2026, 9, 12, 9, 17, tzinfo=UTC), "5m")
    assert value == datetime(2026, 9, 12, 9, 15, tzinfo=UTC)


def test_aggregation_uses_ohlcv_semantics() -> None:
    result = aggregate_bars([make_bar(15), make_bar(16, close="103"), make_bar(17)], "3m")
    assert len(result) == 1
    bar = result[0]
    assert bar.open == Decimal("100")
    assert bar.high == Decimal("119")
    assert bar.low == Decimal("99")
    assert bar.close == Decimal("101")
    assert bar.volume == 348


def test_provisional_bars_are_excluded_by_default() -> None:
    result = aggregate_bars([make_bar(15), make_bar(16, final=False)], "3m")
    assert result[0].volume == 115
    assert result[0].close == Decimal("101")


def test_unsupported_timeframe_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported timeframe"):
        bucket_start(datetime.now(UTC), "2m")
