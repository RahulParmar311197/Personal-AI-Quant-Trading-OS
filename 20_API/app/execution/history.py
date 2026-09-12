"""Provider-neutral durable execution history contracts."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class FillIngestRequest:
    """One immutable broker execution/fill received from a provider."""

    broker_fill_id: str
    client_order_id: str
    broker_order_id: str | None
    instrument_id: str
    side: str
    quantity: Decimal
    fill_price: Decimal
    fee: Decimal
    event_time: datetime
    source: str

    def __post_init__(self) -> None:
        if not self.broker_fill_id.strip():
            raise ValueError("broker_fill_id cannot be empty")
        if not self.client_order_id.strip():
            raise ValueError("client_order_id cannot be empty")
        if not self.instrument_id.strip():
            raise ValueError("instrument_id cannot be empty")
        if self.side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.fill_price <= 0:
            raise ValueError("fill_price must be positive")
        if self.fee < 0:
            raise ValueError("fee cannot be negative")
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")
        if not self.source.strip():
            raise ValueError("source cannot be empty")
