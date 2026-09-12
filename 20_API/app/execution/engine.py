"""Safety-first execution orchestration with optional durable persistence."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.brokers.contracts import BrokerAdapter, BrokerOrderRequest, BrokerOrderResult
from app.execution.lifecycle import DurableOrderKey, OrderLifecycleEvent
from app.execution.repository import ExecutionOrderRepository
from app.risk.engine import RiskDecision


@dataclass(frozen=True)
class ExecutionIntent:
    client_order_id: str
    instrument_id: str
    side: str
    event_time: datetime
    strategy_id: str = "unknown"

    def __post_init__(self) -> None:
        if not self.client_order_id.strip() or not self.instrument_id.strip():
            raise ValueError("execution identity cannot be empty")
        if self.side not in ("BUY", "SELL"):
            raise ValueError("execution side must be BUY or SELL")
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")
        if not self.strategy_id.strip():
            raise ValueError("strategy_id cannot be empty")


@dataclass(frozen=True)
class ExecutionResult:
    accepted: bool
    broker_result: BrokerOrderResult | None
    reason: str


class ExecutionEngine:
    """Forward orders only after RiskEngine authorization.

    ``repository`` is optional for backwards-compatible unit usage. Production
    execution must supply an ``ExecutionOrderRepository`` backed by the same
    database transaction used by the execution workflow.
    """

    def __init__(
        self,
        broker: BrokerAdapter,
        live_enabled: bool = False,
        repository: ExecutionOrderRepository | None = None,
    ) -> None:
        self.broker = broker
        self.live_enabled = live_enabled
        self.repository = repository
        self._submitted_client_ids: set[str] = set()

    @staticmethod
    def _lifecycle_status(result: BrokerOrderResult) -> str:
        mapping = {
            "PENDING": "SUBMITTED",
            "OPEN": "ACKNOWLEDGED",
            "PARTIALLY_FILLED": "PARTIALLY_FILLED",
            "FILLED": "FILLED",
            "CANCELLED": "CANCELLED",
            "REJECTED": "REJECTED",
        }
        return mapping[result.status]

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
        if not self.live_enabled:
            return ExecutionResult(False, None, "live execution is disabled")
        if not self.broker.healthcheck():
            return ExecutionResult(False, None, "broker healthcheck failed")

        if self.repository is not None:
            existing = self.repository.get(intent.client_order_id)
            if existing is not None:
                if existing.status in ("UNKNOWN", "SUBMITTED", "ACKNOWLEDGED", "PARTIALLY_FILLED"):
                    return ExecutionResult(False, None, "existing durable order requires reconciliation")
                return ExecutionResult(False, None, "duplicate client order id")
            self.repository.reserve(
                key=DurableOrderKey(
                    client_order_id=intent.client_order_id,
                    strategy_id=intent.strategy_id,
                    signal_event_time=intent.event_time,
                ),
                instrument_id=intent.instrument_id,
                side=intent.side,
                order_type=order_type,
                quantity=quantity,
                created_at=intent.event_time,
            )
        elif intent.client_order_id in self._submitted_client_ids:
            return ExecutionResult(False, None, "duplicate client order id")

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

        try:
            result = self.broker.place_order(request)
        except Exception as exc:
            if self.repository is not None:
                self.repository.transition(
                    intent.client_order_id,
                    OrderLifecycleEvent(
                        client_order_id=intent.client_order_id,
                        status="UNKNOWN",
                        event_time=datetime.now(timezone.utc),
                        message=f"ambiguous broker response: {type(exc).__name__}",
                    ),
                )
            return ExecutionResult(False, None, "ambiguous broker response; reconciliation required")

        self._submitted_client_ids.add(intent.client_order_id)
        if self.repository is not None:
            self.repository.transition(
                intent.client_order_id,
                OrderLifecycleEvent(
                    client_order_id=intent.client_order_id,
                    status=self._lifecycle_status(result),
                    event_time=datetime.now(timezone.utc),
                    broker_order_id=result.broker_order_id,
                    message=result.message,
                ),
                filled_quantity=result.filled_quantity,
            )
        return ExecutionResult(True, result, "broker order submitted")
