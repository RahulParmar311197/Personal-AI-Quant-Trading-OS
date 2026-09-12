"""Transport-neutral contracts for historical market-data ingestion."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Quality = Literal["VALID", "DEGRADED", "STALE", "INVALID"]


class HistoricalBarRequest(BaseModel):
    """Point-in-time-safe request for a bounded historical bar range."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    instrument_id: str = Field(min_length=1, max_length=128)
    timeframe: str = Field(min_length=1, max_length=16)
    start_time: datetime
    end_time: datetime
    provider: str = Field(min_length=1, max_length=64)
    chunk_size: int = Field(default=1_000, ge=1, le=100_000)

    @model_validator(mode="after")
    def validate_range(self) -> "HistoricalBarRequest":
        if self.start_time.tzinfo is None or self.end_time.tzinfo is None:
            raise ValueError("start_time and end_time must be timezone-aware")
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")
        return self


class HistoricalBar(BaseModel):
    """Normalized provider-independent OHLCV bar."""

    model_config = ConfigDict(extra="forbid")

    instrument_id: str = Field(min_length=1, max_length=128)
    timeframe: str = Field(min_length=1, max_length=16)
    event_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int = Field(ge=0)
    source: str = Field(min_length=1, max_length=64)
    sequence: int | None = Field(default=None, ge=0)
    is_final: bool = True
    quality: Quality = "VALID"

    @model_validator(mode="after")
    def validate_ohlcv(self) -> "HistoricalBar":
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")
        if self.high < self.low:
            raise ValueError("high must be greater than or equal to low")
        if self.high < self.open or self.high < self.close:
            raise ValueError("high must contain open and close")
        if self.low > self.open or self.low > self.close:
            raise ValueError("low must contain open and close")
        return self


class HistoricalBarResult(BaseModel):
    """Provider result after normalization, before persistence."""

    model_config = ConfigDict(extra="forbid")

    request: HistoricalBarRequest
    bars: list[HistoricalBar]
    next_start_time: datetime | None = None
    provider_cursor: str | None = None
    complete: bool
