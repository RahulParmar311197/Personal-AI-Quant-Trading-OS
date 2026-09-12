"""Deterministic multi-timeframe OHLCV aggregation.

The aggregator is intentionally independent of providers and trading logic.
It consumes canonical bars and produces the same result for historical and
live data, provided the same finalized input bars are supplied.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable

from app.market_data.contracts import HistoricalBar


TIMEFRAME_SECONDS: dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1w": 604800,
}


@dataclass(frozen=True)
class AggregatedBar:
    instrument_id: str
    timeframe: str
    event_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    source: str
    is_final: bool


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def bucket_start(timestamp: datetime, timeframe: str) -> datetime:
    """Return the UTC epoch-aligned start of a fixed-duration bucket."""
    seconds = TIMEFRAME_SECONDS.get(timeframe)
    if seconds is None:
        raise ValueError(f"unsupported timeframe: {timeframe}")
    ts = _utc(timestamp)
    epoch = int(ts.timestamp())
    return datetime.fromtimestamp((epoch // seconds) * seconds, tz=timezone.utc)


def aggregate_bars(
    bars: Iterable[HistoricalBar],
    timeframe: str,
    *,
    finalized_only: bool = True,
) -> list[AggregatedBar]:
    """Aggregate canonical bars without filling gaps or using future bars."""
    if timeframe not in TIMEFRAME_SECONDS:
        raise ValueError(f"unsupported timeframe: {timeframe}")

    ordered = sorted((_validate_input(bar) for bar in bars), key=lambda bar: bar.event_time)
    if finalized_only:
        ordered = [bar for bar in ordered if bar.is_final]

    groups: dict[tuple[str, datetime], list[HistoricalBar]] = {}
    for bar in ordered:
        groups.setdefault((bar.instrument_id, bucket_start(bar.event_time, timeframe)), []).append(bar)

    result: list[AggregatedBar] = []
    for (instrument_id, start), group in sorted(groups.items(), key=lambda item: item[0][1]):
        group.sort(key=lambda bar: bar.event_time)
        result.append(
            AggregatedBar(
                instrument_id=instrument_id,
                timeframe=timeframe,
                event_time=start,
                open=group[0].open,
                high=max(bar.high for bar in group),
                low=min(bar.low for bar in group),
                close=group[-1].close,
                volume=sum(bar.volume for bar in group),
                source="aggregate",
                is_final=all(bar.is_final for bar in group),
            )
        )
    return result


def _validate_input(bar: HistoricalBar) -> HistoricalBar:
    """Reject malformed data before aggregation."""
    if bar.volume < 0:
        raise ValueError("volume cannot be negative")
    if _utc(bar.event_time) != bar.event_time:
        return bar.model_copy(update={"event_time": _utc(bar.event_time)})
    return bar
