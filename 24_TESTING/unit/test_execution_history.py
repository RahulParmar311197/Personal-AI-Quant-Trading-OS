from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.execution.history import FillIngestRequest

NOW = datetime(2026, 9, 12, 9, 15, tzinfo=timezone.utc)


def test_fill_request_requires_positive_economics() -> None:
    request = FillIngestRequest(
        broker_fill_id="fill-1",
        client_order_id="client-1",
        broker_order_id="broker-1",
        instrument_id="NSE_EQ|ABC",
        side="BUY",
        quantity=Decimal("1"),
        fill_price=Decimal("100"),
        fee=Decimal("0"),
        event_time=NOW,
        source="upstox.sandbox",
    )
    assert request.quantity == Decimal("1")


def test_fill_request_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        FillIngestRequest(
            broker_fill_id="fill-1",
            client_order_id="client-1",
            broker_order_id=None,
            instrument_id="NSE_EQ|ABC",
            side="BUY",
            quantity=Decimal("1"),
            fill_price=Decimal("100"),
            fee=Decimal("0"),
            event_time=datetime(2026, 9, 12, 9, 15),
            source="test",
        )
