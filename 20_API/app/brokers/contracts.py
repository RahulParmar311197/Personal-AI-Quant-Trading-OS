"""Provider-neutral broker interface and normalized trading contracts."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

BrokerOrderSide = Literal["BUY", "SELL"]
BrokerOrderType = Literal["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]
BrokerOrderStatus = Literal["PENDING", "OPEN", "PARTIALLY_FILLED", "FILLED", "CANCELLED", "REJECTED"]


@dataclass(frozen=True)
class BrokerCapabilities:
    market_orders: bool = True
    limit_orders: bool = True
    stop_orders: bool = False
    fractional_quantity: bool = False
    streaming: bool = False
    list_orders: bool = False


@dataclass(frozen=True)
class BrokerOrderRequest:
    client_order_id: str
    instrument_id: str
    side: BrokerOrderSide
    order_type: BrokerOrderType
    quantity: Decimal
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.client_order_id.strip() or not self.instrument_id.strip():
            raise ValueError("order identity cannot be empty")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.order_type in ("LIMIT", "STOP_LIMIT") and self.limit_price is None:
            raise ValueError("limit orders require limit_price")
        if self.order_type in ("STOP", "STOP_LIMIT") and self.stop_price is None:
            raise ValueError("stop orders require stop_price")
        if self.limit_price is not None and self.limit_price <= 0:
            raise ValueError("limit_price must be positive")
        if self.stop_price is not None and self.stop_price <= 0:
            raise ValueError("stop_price must be positive")
        if self.created_at is not None and self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


@dataclass(frozen=True)
class BrokerOrderResult:
    broker_order_id: str
    client_order_id: str
    status: BrokerOrderStatus
    filled_quantity: Decimal
    average_fill_price: Decimal | None
    message: str = ""

    def __post_init__(self) -> None:
        if not self.broker_order_id.strip() or not self.client_order_id.strip():
            raise ValueError("order identifiers cannot be empty")
        if self.filled_quantity < 0:
            raise ValueError("filled_quantity cannot be negative")
        if self.average_fill_price is not None and self.average_fill_price <= 0:
            raise ValueError("average_fill_price must be positive")


@dataclass(frozen=True)
class BrokerFill:
    """One provider trade normalized at the broker boundary.

    ``broker_fill_id`` must be the provider's stable trade/fill identifier,
    not a locally generated timestamp or sequence number. Client-order
    identity is resolved from the durable broker-order mapping downstream.
    """

    broker_fill_id: str
    broker_order_id: str
    instrument_id: str
    side: BrokerOrderSide
    quantity: Decimal
    price: Decimal
    event_time: datetime
    fee: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not self.broker_fill_id.strip() or not self.broker_order_id.strip():
            raise ValueError("fill identifiers cannot be empty")
        if not self.instrument_id.strip():
            raise ValueError("instrument_id cannot be empty")
        if self.quantity <= 0 or self.price <= 0:
            raise ValueError("fill quantity and price must be positive")
        if self.fee < 0:
            raise ValueError("fee cannot be negative")
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")


@dataclass(frozen=True)
class BrokerPosition:
    instrument_id: str
    quantity: Decimal
    average_price: Decimal


@dataclass(frozen=True)
class BrokerAccount:
    account_id: str
    currency: str
    cash: Decimal
    equity: Decimal
    positions: tuple[BrokerPosition, ...]


class BrokerAdapter(ABC):
    """Provider-neutral broker boundary."""

    @property
    @abstractmethod
    def capabilities(self) -> BrokerCapabilities:
        raise NotImplementedError

    @abstractmethod
    def place_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> BrokerOrderResult:
        raise NotImplementedError

    @abstractmethod
    def get_order(self, broker_order_id: str) -> BrokerOrderResult:
        raise NotImplementedError

    def list_orders(self) -> tuple[BrokerOrderResult, ...]:
        """Return normalized broker orders when the provider supports it."""
        raise NotImplementedError("broker does not support order listing")

    def list_fills(self) -> tuple[BrokerFill, ...]:
        """Return provider trades for the current reconciliation horizon."""
        raise NotImplementedError("broker does not support fill listing")

    def get_fills(self, broker_order_id: str) -> tuple[BrokerFill, ...]:
        """Return provider trades for one broker order when supported."""
        raise NotImplementedError("broker does not support order fill lookup")

    @abstractmethod
    def get_account(self) -> BrokerAccount:
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> tuple[BrokerPosition, ...]:
        raise NotImplementedError

    @abstractmethod
    def healthcheck(self) -> bool:
        raise NotImplementedError
