"""Read-only reconciliation orchestration for broker state."""

from dataclasses import dataclass
from datetime import datetime, timezone

from app.brokers.contracts import BrokerAdapter, BrokerOrderResult
from app.execution.reconciliation import (
    LocalOrderSnapshot,
    ReconciliationReport,
    ReconciliationService,
)
from app.execution.repository import ExecutionOrderRepository


@dataclass(frozen=True)
class ReconciliationRun:
    """Result of one broker reconciliation pass."""

    started_at: datetime
    completed_at: datetime
    report: ReconciliationReport

    @property
    def healthy(self) -> bool:
        return self.report.healthy


class ReconciliationRunner:
    """Fetch broker state and compare it with durable local state.

    The runner is intentionally read-only. A mismatch never triggers an order,
    retry, cancellation, or mutation at the broker. Operators must resolve
    discrepancies before execution is permitted to continue.
    """

    def __init__(
        self,
        repository: ExecutionOrderRepository,
        broker: BrokerAdapter,
        service: ReconciliationService | None = None,
    ) -> None:
        self.repository = repository
        self.broker = broker
        self.service = service or ReconciliationService()

    def run(self) -> ReconciliationRun:
        started = datetime.now(timezone.utc)
        if not self.broker.healthcheck():
            from app.execution.reconciliation import ReconciliationFinding

            report = ReconciliationReport(
                (
                    ReconciliationFinding(
                        "BROKER_MISSING_LOCALLY",
                        "broker-health",
                        "broker healthcheck failed; reconciliation is inconclusive",
                    ),
                )
            )
            completed = datetime.now(timezone.utc)
            return ReconciliationRun(started, completed, report)

        local_orders = tuple(
            LocalOrderSnapshot(
                client_order_id=row.client_order_id,
                broker_order_id=row.broker_order_id or "",
                status=row.status,
                quantity=row.requested_quantity,
                filled_quantity=row.filled_quantity,
                instrument_id=row.instrument_id,
            )
            for row in self.repository.find_active()
            if row.broker_order_id
        )
        broker_orders: tuple[BrokerOrderResult, ...] = tuple(
            self.broker.get_order(item.broker_order_id) for item in local_orders
        )
        report = self.service.reconcile_orders(local_orders, broker_orders)
        completed = datetime.now(timezone.utc)
        return ReconciliationRun(started, completed, report)
