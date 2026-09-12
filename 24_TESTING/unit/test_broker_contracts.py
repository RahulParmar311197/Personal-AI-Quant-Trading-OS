from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.brokers.contracts import BrokerCapabilities, BrokerOrderRequest


def test_market_order_contract() -> None:
    request = BrokerOrderRequest(
        client_order_id="client-1",
        instrument_id="NIFTY",
        side="BUY",
        order_type="MARKET",
        quantity=Decimal("1"),
        created_at=datetime(2026, 1, 1, 9, 15, tzinfo=timezone.utc),
    )
    assert request.side == "BUY"
    assert request.quantity == Decimal("1")


def test_limit_order_requires_limit_price() -> None:
    with pytest.raises(ValueError, match="limit_price"):
        BrokerOrderRequest("client-1", "NIFTY", "BUY", "LIMIT", Decimal("1"))


def test_stop_order_requires_stop_price() -> None:
    with pytest.raises(ValueError, match="stop_price"):
        BrokerOrderRequest("client-1", "NIFTY", "BUY", "STOP", Decimal("1"))


def test_capabilities_are_explicit() -> None:
    capabilities = BrokerCapabilities(stop_orders=True, streaming=True)
    assert capabilities.stop_orders is True
    assert capabilities.streaming is True


def test_invalid_quantity_rejected() -> None:
    with pytest.raises(ValueError, match="quantity"):
        BrokerOrderRequest("client-1", "NIFTY", "BUY", "MARKET", Decimal("0"))
