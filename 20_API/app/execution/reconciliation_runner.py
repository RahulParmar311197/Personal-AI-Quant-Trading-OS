"""Read-only reconciliation orchestration for broker state."""

from dataclasses import dataclass
from datetime import datetime, timezone

from app.brokers.contracts import BrokerAdapter
from app.execution.reconciliation import (
    LocalOrderSnapshot,
    ReconciliationFinding,
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
    """Fetch broker state and compare it with durable local state."""

    def __init__(
        self,
        repository: ExecutionOrderRepository,
        broker: BrokerAdapter,
        service: ReconciliationService | None = None,
    ) -> None:
        self.repository = repository
        self.broker = broker
        self.service = service or ReconciliationService()

    def run(self, *, local_positions=None) -> ReconciliationRun:
        """Reconcile broker orders and positions against durable local state."""
        started = datetime.now(timezone.utc)
        if not self.broker.healthcheck():
            report = ReconciliationReport(
                (
                    ReconciliationFinding(
                        "BROKER_UNAVAILABLE",
                        "broker-health",
                        "broker healthcheck failed; reconciliation is inconclusive",
                    ),
                )
            )
            completed = datetime.now(timezone.utc)
            return ReconciliationRun(started, completed, report)

        try:
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
            positions = (
                tuple(local_positions)
                if local_positions is not None
                else tuple(self.repository.project_positions())
            )
        except Exception as exc:
            report = ReconciliationReport(
                (
                    ReconciliationFinding(
                        "LOCAL_STATE_UNAVAILABLE",
                        "local-snapshot",
                        f"local reconciliation state failed: {type(exc).__name__}",
                    ),
                )
            )
            completed = datetime.now(timezone.utc)
            return ReconciliationRun(started, completed, report)

        try:
            if self.broker.capabilities.list_orders:
                broker_orders = self.broker.list_orders()
            else:
                broker_orders = tuple(
                    self.broker.get_order(item.broker_order_id) for item in local_orders
                )
            broker_positions = self.broker.get_positions()
        except Exception as exc:
            report = ReconciliationReport(
                (
                    ReconciliationFinding(
                        "BROKER_UNAVAILABLE",
                        "broker-snapshot",
                        f"broker snapshot failed: {type(exc).__name__}",
                    ),
                )
            )
            completed = datetime.now(timezone.utc)
            return ReconciliationRun(started, completed, report)

        order_report = self.service.reconcile_orders(local_orders, broker_orders)
        position_report = self.service.reconcile_positions(positions, broker_positions)
        report = ReconciliationReport(order_report.findings + position_report.findings)
        completed = datetime.now(timezone.utc)
        return ReconciliationRun(started, completed, report)
