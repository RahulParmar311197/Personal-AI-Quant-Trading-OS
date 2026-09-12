"""Execution orchestration between risk authorization and broker adapters."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.brokers.contracts import BrokerAdapter, BrokerOrderRequest, BrokerOrderResult
from app.risk.engine import RiskDecision


@dataclass(frozen=True)
class ExecutionIntent:
    client_order_id: str
    instrument_id: str
    side: str
    event_time: datetime

    def __post_init__(self) -> None:
        if not self.client_order_id.strip() or not self.instrument_id.strip():
            raise ValueError("execution identity cannot be empty")
        if self.side not in ("BUY", "SELL"):
            raise ValueError("execution side must be BUY or SELL")
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")


@dataclass(frozen=True)
class ExecutionResult:
    accepted: bool
    broker_result: BrokerOrderResult | None
    reason: str


class ExecutionEngine:
    """Only forwards an order after explicit RiskEngine authorization.

    This V1 engine defaults to paper-only behavior. A real adapter can be
    injected for later sandbox testing, but live execution is blocked unless
    the caller explicitly opts in at construction time.
    """

    def __init__(self, broker: BrokerAdapter, live_enabled: bool = False) -> None:
        self.broker = broker
        self.live_enabled = live_enabled
        self._submitted_client_ids: set[str] = set()

    def execute(
        self,
        intent: ExecutionIntent,
        risk: RiskDecision,
        quantity: Decimal,
        order_type: str = "MARKET",
        limit_price: Decimal | None = None,
        stop_price: Decimal | None = None,
    ) -> ExecutionResult:
        if not risk.allowed:
            return ExecutionResult(False, None, "risk authorization denied")
        if quantity <= 0 or quantity > risk.quantity:
            return ExecutionResult(False, None, "requested quantity exceeds risk authorization")
        if intent.client_order_id in self._submitted_client_ids:
            return ExecutionResult(False, None, "duplicate client order id")
        if not self.live_enabled:
            return ExecutionResult(False, None, "live execution is disabled")
        if not self.broker.healthcheck():
            return ExecutionResult(False, None, "broker healthcheck failed")

        request = BrokerOrderRequest(
            client_order_id=intent.client_order_id,
            instrument_id=intent.instrument_id,
            side=intent.side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
            created_at=intent.event_time.astimezone(timezone.utc),
        )
        result = self.broker.place_order(request)
        self._submitted_client_ids.add(intent.client_order_id)
        return ExecutionResult(True, result, "broker order submitted")
