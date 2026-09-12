"""Upstox sandbox adapter.

The adapter targets Upstox order V3 for order submission/cancellation and the
current V2 order-book/details/account endpoints for reconciliation reads.
No credentials are stored in source control. Live use requires an explicit
non-sandbox base URL and remains blocked by the execution engine unless live
execution is explicitly enabled.
"""

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.brokers.contracts import (
    BrokerAccount,
    BrokerAdapter,
    BrokerCapabilities,
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerPosition,
)

Transport = Callable[[str, str, dict[str, str], bytes | None, float], tuple[int, dict[str, Any]]]


@dataclass(frozen=True)
class UpstoxConfig:
    access_token: str
    base_url: str = "https://sandbox.upstox.com"
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if not self.access_token.strip():
            raise ValueError("access_token cannot be empty")
        if not self.base_url.startswith("https://"):
            raise ValueError("base_url must use HTTPS")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


class UpstoxAdapter(BrokerAdapter):
    """Concrete Upstox adapter with sandbox-first defaults."""

    def __init__(self, config: UpstoxConfig, transport: Transport | None = None) -> None:
        self.config = config
        self._transport = transport or self._http_transport

    @property
    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            market_orders=True,
            limit_orders=True,
            stop_orders=True,
            fractional_quantity=False,
            streaming=False,
            list_orders=True,
        )

    def place_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        if request.order_type == "STOP_LIMIT":
            order_type = "SL"
        elif request.order_type == "STOP":
            order_type = "SL-M"
        else:
            order_type = request.order_type

        payload = {
            "quantity": self._integer_quantity(request.quantity),
            "product": "I",
            "validity": "DAY",
            "price": float(request.limit_price or 0),
            "tag": request.client_order_id,
            "instrument_token": request.instrument_id,
            "order_type": order_type,
            "transaction_type": request.side,
            "disclosed_quantity": 0,
            "trigger_price": float(request.stop_price or 0),
            "is_amo": False,
            "slice": False,
            "market_protection": -1,
        }
        status_code, body = self._request("POST", "/v3/order/place", payload)
        data = body.get("data") or {}
        order_ids = data.get("order_ids") or []
        if status_code >= 400 or not order_ids:
            raise RuntimeError(self._error_message(body, status_code))
        return BrokerOrderResult(
            broker_order_id=str(order_ids[0]),
            client_order_id=request.client_order_id,
            status="PENDING",
            filled_quantity=Decimal("0"),
            average_fill_price=None,
            message="Upstox order accepted by API",
        )

    def cancel_order(self, broker_order_id: str) -> BrokerOrderResult:
        if not broker_order_id.strip():
            raise ValueError("broker_order_id cannot be empty")
        status_code, body = self._request(
            "DELETE", f"/v3/order/cancel?{urlencode({'order_id': broker_order_id})}", None
        )
        if status_code >= 400:
            raise RuntimeError(self._error_message(body, status_code))
        return BrokerOrderResult(
            broker_order_id=broker_order_id,
            client_order_id=str((body.get("data") or {}).get("order_id", broker_order_id)),
            status="CANCELLED",
            filled_quantity=Decimal("0"),
            average_fill_price=None,
            message="Upstox cancellation accepted",
        )

    def get_order(self, broker_order_id: str) -> BrokerOrderResult:
        status_code, body = self._request(
            "GET", f"/v2/order/details?{urlencode({'order_id': broker_order_id})}", None
        )
        if status_code >= 400:
            raise RuntimeError(self._error_message(body, status_code))
        data = body.get("data") or {}
        return self._map_order(data, broker_order_id)

    def list_orders(self) -> tuple[BrokerOrderResult, ...]:
        """Return the current-day Upstox order book for full reconciliation discovery."""
        status_code, body = self._request("GET", "/v2/order/retrieve-all", None)
        if status_code >= 400:
            raise RuntimeError(self._error_message(body, status_code))
        data = body.get("data") or []
        if not isinstance(data, list):
            raise RuntimeError("Upstox order book response has invalid data shape")
        return tuple(
            self._map_order(item, str(item.get("order_id", "")))
            for item in data
            if isinstance(item, dict) and str(item.get("order_id", "")).strip()
        )

    def get_account(self) -> BrokerAccount:
        profile_status, profile = self._request("GET", "/v2/user/profile", None)
        if profile_status >= 400:
            raise RuntimeError(self._error_message(profile, profile_status))
        funds_status, funds = self._request("GET", "/v2/user/get-funds-and-margin", None)
        if funds_status >= 400:
            raise RuntimeError(self._error_message(funds, funds_status))
        positions = self.get_positions()
        profile_data = profile.get("data") or {}
        equity = (funds.get("data") or {}).get("equity") or {}
        cash = Decimal(str(equity.get("available_margin", 0)))
        return BrokerAccount(
            account_id=str(profile_data.get("user_id", "UPSTOX")),
            currency="INR",
            cash=cash,
            equity=cash,
            positions=positions,
        )

    def get_positions(self) -> tuple[BrokerPosition, ...]:
        status_code, body = self._request("GET", "/v2/portfolio/short-term-positions", None)
        if status_code >= 400:
            raise RuntimeError(self._error_message(body, status_code))
        result: list[BrokerPosition] = []
        for item in body.get("data") or []:
            result.append(
                BrokerPosition(
                    instrument_id=str(item.get("instrument_token", "")),
                    quantity=Decimal(str(item.get("quantity", item.get("net_quantity", 0)))),
                    average_price=Decimal(str(item.get("average_price", 0))),
                )
            )
        return tuple(result)

    def healthcheck(self) -> bool:
        try:
            status_code, _ = self._request("GET", "/v2/user/profile", None)
            return status_code < 400
        except (OSError, RuntimeError, ValueError):
            return False

    @staticmethod
    def _integer_quantity(quantity: Decimal) -> int:
        if quantity != quantity.to_integral_value():
            raise ValueError("Upstox adapter requires whole-number quantities")
        return int(quantity)

    @staticmethod
    def _map_order(data: dict[str, Any], broker_order_id: str) -> BrokerOrderResult:
        raw_status = str(data.get("status", "")).lower()
        mapping = {
            "complete": "FILLED",
            "complete - placed": "FILLED",
            "open": "OPEN",
            "pending": "PENDING",
            "put order req received": "PENDING",
            "cancelled": "CANCELLED",
            "rejected": "REJECTED",
            "partially filled": "PARTIALLY_FILLED",
        }
        status = mapping.get(raw_status, "PENDING")
        client_order_id = str(data.get("tag") or data.get("order_ref_id") or broker_order_id)
        return BrokerOrderResult(
            broker_order_id=str(data.get("order_id", broker_order_id)),
            client_order_id=client_order_id,
            status=status,
            filled_quantity=Decimal(str(data.get("filled_quantity", 0))),
            average_fill_price=(
                Decimal(str(data["average_price"]))
                if data.get("average_price") not in (None, 0, 0.0)
                else None
            ),
            message=str(data.get("status_message") or ""),
        )

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None
    ) -> tuple[int, dict[str, Any]]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        return self._transport(method, f"{self.config.base_url.rstrip('/')}{path}", self._headers(), body, self.config.timeout_seconds)

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.access_token}",
        }

    @staticmethod
    def _http_transport(
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
    ) -> tuple[int, dict[str, Any]]:
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
                return response.status, json.loads(raw) if raw else {}
        except HTTPError as exc:
            raw = exc.read().decode("utf-8")
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = {"errors": [{"message": raw or str(exc)}]}
            return exc.code, parsed
        except URLError as exc:
            raise RuntimeError(f"Upstox network error: {exc.reason}") from exc

    @staticmethod
    def _error_message(body: dict[str, Any], status_code: int) -> str:
        errors = body.get("errors") or []
        if errors and isinstance(errors[0], dict):
            return str(errors[0].get("message") or errors[0].get("error") or f"HTTP {status_code}")
        return str(body.get("message") or f"Upstox request failed with HTTP {status_code}")
