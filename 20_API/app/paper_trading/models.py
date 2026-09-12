"""Immutable paper-trading domain models."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

PaperSide = Literal["LONG", "SHORT"]
OrderStatus = Literal["OPEN", "FILLED", "CANCELLED"]


@dataclass(frozen=True)
class PaperOrder:
    order_id: str
    instrument_id: str
    side: PaperSide
    quantity: Decimal
    created_at: datetime
    status: OrderStatus = "OPEN"

    def __post_init__(self) -> None:
        if not self.order_id.strip() or not self.instrument_id.strip():
            raise ValueError("order identity cannot be empty")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


@dataclass(frozen=True)
class PaperFill:
    fill_id: str
    order_id: str
    instrument_id: str
    side: PaperSide
    quantity: Decimal
    price: Decimal
    event_time: datetime
    fee: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not self.fill_id.strip() or not self.order_id.strip():
            raise ValueError("fill identity cannot be empty")
        if self.quantity <= 0 or self.price <= 0:
            raise ValueError("fill quantity and price must be positive")
        if self.fee < 0:
            raise ValueError("fee cannot be negative")
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")


@dataclass(frozen=True)
class PaperPosition:
    instrument_id: str
    quantity: Decimal
    average_price: Decimal
    realized_pnl: Decimal = Decimal("0")

    @property
    def side(self) -> PaperSide | None:
        if self.quantity > 0:
            return "LONG"
        if self.quantity < 0:
            return "SHORT"
        return None


@dataclass(frozen=True)
class PaperAccount:
    initial_cash: Decimal
    cash: Decimal
    realized_pnl: Decimal
    fees_paid: Decimal
    orders: tuple[PaperOrder, ...]
    fills: tuple[PaperFill, ...]
    positions: tuple[PaperPosition, ...]

    @classmethod
    def create(cls, initial_cash: Decimal) -> "PaperAccount":
        if initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        return cls(initial_cash, initial_cash, Decimal("0"), Decimal("0"), (), (), ())
