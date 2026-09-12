"""Provider-neutral live market-data adapter boundary.

This module intentionally stops at canonical event validation and delivery. It
contains no order, broker, or execution capability.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

LiveQuality = Literal["VALID", "DEGRADED", "STALE", "INVALID"]


class LiveMarketDataEvent(BaseModel):
    """Canonical envelope for a single live provider event."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID = Field(default_factory=uuid4)
    instrument_id: str = Field(min_length=1, max_length=128)
    exchange: str = Field(min_length=1, max_length=32)
    segment: str = Field(min_length=1, max_length=32)
    symbol: str = Field(min_length=1, max_length=128)
    provider: str = Field(min_length=1, max_length=64)
    provider_event_id: str | None = Field(default=None, max_length=128)
    event_time: datetime
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    quality: LiveQuality = "VALID"
    sequence: int | None = Field(default=None, ge=0)
    payload: dict[str, Any]

    @model_validator(mode="after")
    def validate_timestamps(self) -> "LiveMarketDataEvent":
        if self.event_time.tzinfo is None or self.ingested_at.tzinfo is None:
            raise ValueError("event_time and ingested_at must be timezone-aware")
        if self.ingested_at < self.event_time:
            raise ValueError("ingested_at cannot precede event_time")
        return self


class LiveDataProvider(ABC):
    """Adapter contract for a websocket/streaming provider."""

    name: str

    @abstractmethod
    def connect(self, instruments: list[str]) -> None:
        """Start a provider stream for canonical instrument IDs."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """Stop the provider stream and release resources."""
        raise NotImplementedError

    @abstractmethod
    def poll(self) -> list[LiveMarketDataEvent]:
        """Return newly received canonical events without placing orders."""
        raise NotImplementedError


class LiveEventGuard:
    """Enforce sequencing, deduplication and freshness at the live boundary."""

    def __init__(self, stale_after_seconds: float = 10.0) -> None:
        if stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")
        self.stale_after_seconds = stale_after_seconds
        self._seen_provider_events: set[tuple[str, str]] = set()
        self._last_sequence: dict[tuple[str, str], int] = {}

    def accept(self, event: LiveMarketDataEvent, now: datetime | None = None) -> LiveMarketDataEvent | None:
        """Return accepted event, or None for a duplicate/out-of-order event."""
        if now is None:
            now = datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        if event.provider_event_id is not None:
            identity = (event.provider, event.provider_event_id)
            if identity in self._seen_provider_events:
                return None
            self._seen_provider_events.add(identity)

        if event.sequence is not None:
            key = (event.provider, event.instrument_id)
            previous = self._last_sequence.get(key)
            if previous is not None and event.sequence <= previous:
                return None
            self._last_sequence[key] = event.sequence

        age = (now - event.event_time).total_seconds()
        if age < 0:
            raise ValueError("event_time cannot be in the future relative to processing time")
        if age > self.stale_after_seconds and event.quality == "VALID":
            return event.model_copy(update={"quality": "STALE"})
        return event
