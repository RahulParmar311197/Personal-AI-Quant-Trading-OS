"""Deterministic independent pre-trade risk engine.

Risk is an authorization boundary. Strategy and decision layers can propose
intent, but only this engine can authorize an executable quantity in V1.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

RiskAction = Literal["LONG", "SHORT"]


@dataclass(frozen=True)
class RiskConfig:
    """Hard risk limits. All monetary values use the account currency."""

    risk_per_trade: Decimal = Decimal("0.01")
    max_daily_loss: Decimal = Decimal("0.03")
    max_position_notional: Decimal = Decimal("1.0")
    max_open_positions: int = 1
    minimum_stop_distance_pct: Decimal = Decimal("0.001")
    maximum_stop_distance_pct: Decimal = Decimal("0.05")

    def __post_init__(self) -> None:
        if not Decimal("0") < self.risk_per_trade <= Decimal("1"):
            raise ValueError("risk_per_trade must be between 0 and 1")
        if not Decimal("0") < self.max_daily_loss <= Decimal("1"):
            raise ValueError("max_daily_loss must be between 0 and 1")
        if not Decimal("0") < self.max_position_notional:
            raise ValueError("max_position_notional must be positive")
        if self.max_open_positions < 1:
            raise ValueError("max_open_positions must be at least 1")
        if not Decimal("0") < self.minimum_stop_distance_pct <= self.maximum_stop_distance_pct:
            raise ValueError("stop distance bounds are invalid")


@dataclass(frozen=True)
class RiskRequest:
    """Decision proposal plus account/exposure state presented to risk."""

    event_time: datetime
    action: RiskAction
    entry_price: Decimal
    stop_price: Decimal
    account_equity: Decimal
    daily_realized_pnl: Decimal
    open_positions: int = 0
    current_notional: Decimal = Decimal("0")
    requested_quantity: Decimal | None = None
    kill_switch: bool = False
    live_trading_enabled: bool = False

    def __post_init__(self) -> None:
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")
        if self.entry_price <= 0 or self.stop_price <= 0:
            raise ValueError("prices must be positive")
        if self.account_equity <= 0:
            raise ValueError("account_equity must be positive")
        if self.open_positions < 0:
            raise ValueError("open_positions cannot be negative")
        if self.current_notional < 0:
            raise ValueError("current_notional cannot be negative")
        if self.requested_quantity is not None and self.requested_quantity <= 0:
            raise ValueError("requested_quantity must be positive")


@dataclass(frozen=True)
class RiskDecision:
    """Auditable authorization result. Authorization is separate from order execution."""

    event_time: datetime
    allowed: bool
    action: RiskAction
    quantity: Decimal
    risk_amount: Decimal
    notional: Decimal
    reasons: tuple[str, ...]


class RiskEngine:
    """Hard pre-trade risk gate independent of strategy and AI."""

    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()

    def evaluate(self, request: RiskRequest) -> RiskDecision:
        timestamp = request.event_time.astimezone(timezone.utc)
        reasons: list[str] = []

        if request.kill_switch:
            return self._deny(request, timestamp, "kill switch is active")
        if not request.live_trading_enabled:
            reasons.append("live trading disabled; risk decision is research/paper authorization only")
        if request.open_positions >= self.config.max_open_positions:
            return self._deny(request, timestamp, "maximum open positions reached")
        if request.daily_realized_pnl <= -request.account_equity * self.config.max_daily_loss:
            return self._deny(request, timestamp, "maximum daily loss reached")

        stop_distance = abs(request.entry_price - request.stop_price) / request.entry_price
        if stop_distance < self.config.minimum_stop_distance_pct:
            return self._deny(request, timestamp, "stop distance is below minimum")
        if stop_distance > self.config.maximum_stop_distance_pct:
            return self._deny(request, timestamp, "stop distance exceeds maximum")

        max_risk = request.account_equity * self.config.risk_per_trade
        quantity_by_risk = max_risk / abs(request.entry_price - request.stop_price)
        quantity_by_notional = max(
            Decimal("0"),
            (request.account_equity * self.config.max_position_notional - request.current_notional)
            / request.entry_price,
        )
        quantity = min(quantity_by_risk, quantity_by_notional)
        if request.requested_quantity is not None:
            quantity = min(quantity, request.requested_quantity)
        if quantity <= 0:
            return self._deny(request, timestamp, "position limits leave no permitted quantity")

        notional = quantity * request.entry_price
        risk_amount = quantity * abs(request.entry_price - request.stop_price)
        reasons.append("risk-per-trade limit satisfied")
        reasons.append("position-notional limit satisfied")
        reasons.append("stop distance validated")
        return RiskDecision(timestamp, True, request.action, quantity, risk_amount, notional,
                            tuple(reasons))

    @staticmethod
    def _deny(request: RiskRequest, timestamp: datetime, reason: str) -> RiskDecision:
        return RiskDecision(timestamp, False, request.action, Decimal("0"), Decimal("0"),
                            Decimal("0"), (reason,))
