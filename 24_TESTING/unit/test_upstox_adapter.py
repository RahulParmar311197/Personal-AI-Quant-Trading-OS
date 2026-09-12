from decimal import Decimal

import pytest

from app.brokers.contracts import BrokerOrderRequest
from app.brokers.upstox import UpstoxAdapter, UpstoxConfig


def fake_transport(method, url, headers, body, timeout):
    assert headers["Authorization"] == "Bearer sandbox-token"
    if method == "POST" and url.endswith("/v3/order/place"):
        return 200, {"status": "success", "data": {"order_ids": ["UP-1"]}}
    if method == "DELETE" and "/v3/order/cancel?" in url:
        return 200, {"status": "success", "data": {"order_id": "UP-1"}}
    if method == "GET" and "/v2/order/details?" in url:
        return 200, {"status": "success", "data": {"order_id": "UP-1", "tag": "client-1", "status": "complete", "filled_quantity": 1, "average_price": 100}}
    if method == "GET" and url.endswith("/v2/user/profile"):
        return 200, {"status": "success", "data": {"user_id": "U1"}}
    if method == "GET" and url.endswith("/v2/user/get-funds-and-margin"):
        return 200, {"status": "success", "data": {"equity": {"available_margin": 100000}}}
    if method == "GET" and url.endswith("/v2/portfolio/short-term-positions"):
        return 200, {"status": "success", "data": [{"instrument_token": "NSE_EQ|ABC", "quantity": 1, "average_price": 100}]}
    raise AssertionError(f"unexpected request: {method} {url}")


def request() -> BrokerOrderRequest:
    return BrokerOrderRequest("client-1", "NSE_EQ|ABC", "BUY", "MARKET", Decimal("1"))


def test_upstox_place_order_maps_v3_response() -> None:
    adapter = UpstoxAdapter(UpstoxConfig("sandbox-token"), fake_transport)
    result = adapter.place_order(request())
    assert result.broker_order_id == "UP-1"
    assert result.client_order_id == "client-1"
    assert result.status == "PENDING"


def test_upstox_order_and_cancel_mapping() -> None:
    adapter = UpstoxAdapter(UpstoxConfig("sandbox-token"), fake_transport)
    result = adapter.get_order("UP-1")
    assert result.status == "FILLED"
    assert result.filled_quantity == Decimal("1")
    cancelled = adapter.cancel_order("UP-1")
    assert cancelled.status == "CANCELLED"


def test_upstox_account_and_positions() -> None:
    adapter = UpstoxAdapter(UpstoxConfig("sandbox-token"), fake_transport)
    account = adapter.get_account()
    assert account.account_id == "U1"
    assert account.cash == Decimal("100000")
    assert account.positions[0].instrument_id == "NSE_EQ|ABC"


def test_upstox_rejects_fractional_quantity() -> None:
    adapter = UpstoxAdapter(UpstoxConfig("sandbox-token"), fake_transport)
    with pytest.raises(ValueError, match="whole-number"):
        adapter.place_order(
            BrokerOrderRequest("client-1", "NSE_EQ|ABC", "BUY", "MARKET", Decimal("1.5"))
        )
