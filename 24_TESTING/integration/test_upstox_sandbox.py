"""Opt-in Upstox sandbox acceptance test.

This test never runs against the live trading environment. It requires an
explicit sandbox access token plus a sandbox-safe instrument and limit price.
The order is placed as a LIMIT order and immediately cancelled so the harness
can validate authentication, placement, inspection, cancellation, and order
book discovery without intentionally sending a market order.
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest

from app.brokers.contracts import BrokerOrderRequest
from app.brokers.upstox import UpstoxAdapter, UpstoxConfig

TOKEN_ENV = "UPSTOX_SANDBOX_ACCESS_TOKEN"
INSTRUMENT_ENV = "UPSTOX_SANDBOX_INSTRUMENT_TOKEN"
PRICE_ENV = "UPSTOX_SANDBOX_LIMIT_PRICE"
BASE_URL_ENV = "UPSTOX_SANDBOX_BASE_URL"


def _required_environment() -> tuple[str, str, Decimal] | None:
    token = os.getenv(TOKEN_ENV, "").strip()
    instrument = os.getenv(INSTRUMENT_ENV, "").strip()
    price_raw = os.getenv(PRICE_ENV, "").strip()
    if not token or not instrument or not price_raw:
        return None
    try:
        price = Decimal(price_raw)
    except Exception as exc:  # pragma: no cover - defensive env validation
        raise pytest.UsageError(f"{PRICE_ENV} must be a valid decimal") from exc
    if price <= 0:
        raise pytest.UsageError(f"{PRICE_ENV} must be positive")
    return token, instrument, price


def test_upstox_sandbox_order_lifecycle() -> None:
    """Exercise the real sandbox lifecycle only when credentials are supplied."""
    config_values = _required_environment()
    if config_values is None:
        pytest.skip(
            f"opt-in only: set {TOKEN_ENV}, {INSTRUMENT_ENV}, and {PRICE_ENV} "
            "to run against the Upstox sandbox"
        )

    token, instrument, price = config_values
    base_url = os.getenv(BASE_URL_ENV, "https://sandbox.upstox.com").strip()
    if not base_url.startswith("https://"):
        raise pytest.UsageError(f"{BASE_URL_ENV} must use HTTPS")

    adapter = UpstoxAdapter(UpstoxConfig(token, base_url=base_url))
    assert adapter.healthcheck(), "Upstox sandbox authentication/healthcheck failed"

    client_order_id = f"quant-os-sandbox-{os.urandom(8).hex()}"
    result = adapter.place_order(
        BrokerOrderRequest(
            client_order_id=client_order_id,
            instrument_id=instrument,
            side="BUY",
            order_type="LIMIT",
            quantity=Decimal("1"),
            limit_price=price,
        )
    )
    assert result.broker_order_id
    assert result.client_order_id == client_order_id

    inspected = adapter.get_order(result.broker_order_id)
    assert inspected.broker_order_id == result.broker_order_id
    assert inspected.client_order_id == client_order_id

    cancelled = adapter.cancel_order(result.broker_order_id)
    assert cancelled.broker_order_id == result.broker_order_id

    final = adapter.get_order(result.broker_order_id)
    assert final.status in {"CANCELLED", "FILLED", "PARTIALLY_FILLED"}

    discovered = adapter.list_orders()
    assert any(order.broker_order_id == result.broker_order_id for order in discovered)
