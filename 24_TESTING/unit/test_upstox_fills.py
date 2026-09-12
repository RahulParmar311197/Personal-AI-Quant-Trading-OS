from decimal import Decimal

import pytest

from app.brokers.contracts import BrokerOrderRequest
from app.brokers.upstox import UpstoxAdapter, UpstoxConfig


def make_adapter(responses: dict[str, dict]) -> UpstoxAdapter:
    def transport(method: str, url: str, headers: dict[str, str], body: bytes | None, timeout: float):
        for path, response in responses.items():
            if path in url:
                return 200, response
        raise AssertionError(f"unexpected request: {method} {url}")

    return UpstoxAdapter(UpstoxConfig(access_token="sandbox-token"), transport=transport)


def test_upstox_maps_trade_id_and_ist_timestamp() -> None:
    adapter = make_adapter(
        {
            "/v2/order/trades/get-trades-for-day": {
                "data": [
                    {
                        "trade_id": "trade-42",
                        "order_id": "order-7",
                        "instrument_token": "NSE_EQ|INE000000000",
                        "transaction_type": "BUY",
                        "quantity": 2,
                        "average_price": 101.25,
                        "exchange_timestamp": "12-Sep-2026 09:15:30",
                    }
                ]
            }
        }
    )

    fills = adapter.list_fills()

    assert len(fills) == 1
    assert fills[0].broker_fill_id == "trade-42"
    assert fills[0].broker_order_id == "order-7"
    assert fills[0].quantity == Decimal("2")
    assert fills[0].price == Decimal("101.25")
    assert str(fills[0].event_time.tzinfo) == "Asia/Kolkata"
    assert fills[0].fee == Decimal("0")


def test_upstox_order_trade_lookup_is_scoped_to_order() -> None:
    adapter = make_adapter(
        {
            "/v2/order/trades?": {
                "data": [
                    {
                        "trade_id": "trade-1",
                        "order_id": "order-7",
                        "instrument_token": "NSE_EQ|ABC",
                        "transaction_type": "SELL",
                        "quantity": 1,
                        "average_price": 99.5,
                        "exchange_timestamp": "12-Sep-2026 10:00:00",
                    }
                ]
            }
        }
    )

    fills = adapter.get_fills("order-7")

    assert [fill.broker_fill_id for fill in fills] == ["trade-1"]
    assert fills[0].side == "SELL"


def test_upstox_rejects_trade_without_stable_trade_id() -> None:
    adapter = make_adapter(
        {
            "/v2/order/trades/get-trades-for-day": {
                "data": [
                    {
                        "order_id": "order-7",
                        "instrument_token": "NSE_EQ|ABC",
                        "transaction_type": "BUY",
                        "quantity": 1,
                        "average_price": 100,
                        "exchange_timestamp": "12-Sep-2026 10:00:00",
                    }
                ]
            }
        }
    )

    with pytest.raises(ValueError, match="trade_id"):
        adapter.list_fills()
