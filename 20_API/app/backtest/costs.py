"""Deterministic transaction-cost and fill model for backtesting."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

Side = Literal["LONG", "SHORT"]


@dataclass(frozen=True)
class CostModel:
    fee_bps: Decimal = Decimal("3")
    slippage_bps: Decimal = Decimal("1")
    spread_bps: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if min(self.fee_bps, self.slippage_bps, self.spread_bps) < 0:
            raise ValueError("cost parameters cannot be negative")

    def execution_price(self, reference_price: Decimal, side: Side) -> Decimal:
        """Apply half-spread plus adverse slippage to a reference price."""
        if reference_price <= 0:
            raise ValueError("reference_price must be positive")
        adverse_bps = self.slippage_bps + (self.spread_bps / Decimal("2"))
        multiplier = Decimal("1") + adverse_bps / Decimal("10000")
        if side == "LONG":
            return reference_price * multiplier
        return reference_price / multiplier

    def fee(self, execution_price: Decimal, quantity: Decimal) -> Decimal:
        if execution_price <= 0 or quantity <= 0:
            raise ValueError("execution_price and quantity must be positive")
        return execution_price * quantity * self.fee_bps / Decimal("10000")

    def round_trip_cost(self, entry: Decimal, exit: Decimal, quantity: Decimal) -> Decimal:
        return self.fee(entry, quantity) + self.fee(exit, quantity)
