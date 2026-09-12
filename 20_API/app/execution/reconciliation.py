"""Broker reconciliation contracts for execution safety."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.brokers.contracts import BrokerOrderResult, BrokerPosition

ReconciliationKind = Literal[
    "MATCH",
    "LOCAL_MISSING_AT_BROKER",
    "BROKER_MISSING_LOCALLY",
    "STATUS_MISMATCH",
    "FILL_QUANTITY_MISMATCH",
    "POSITION_MISMATCH",
    "BROKER_UNAVAILABLE",
]


@dataclass(frozen=True)
class LocalOrderSnapshot:
    client_order_id: str
    broker_order_id: str
    status: str
    quantity: Decimal
    filled_quantity: Decimal
    instrument_id: str


@dataclass(frozen=True)
class ReconciliationFinding:
    kind: ReconciliationKind
    identity: str
    message: str
    safe_to_continue: bool = False


@dataclass(frozen=True)
class ReconciliationReport:
    findings: tuple[ReconciliationFinding, ...]

    @property
    def healthy(self) -> bool:
        return not self.findings


class ReconciliationService:
    """Compare local durable state with normalized broker snapshots.

    Any discrepancy is fail-closed. This service never submits, retries, or
    cancels an order as a side effect of reconciliation.
    """

    def reconcile_orders(
        self,
        local_orders: tuple[LocalOrderSnapshot, ...],
        broker_orders: tuple[BrokerOrderResult, ...],
    ) -> ReconciliationReport:
        local_by_broker = {item.broker_order_id: item for item in local_orders}
        broker_by_id = {item.broker_order_id: item for item in broker_orders}
        findings: list[ReconciliationFinding] = []

        for broker_id, local in local_by_broker.items():
            broker = broker_by_id.get(broker_id)
            if broker is None:
                findings.append(ReconciliationFinding(
                    "LOCAL_MISSING_AT_BROKER", broker_id,
                    "local order has no matching broker order snapshot",
                ))
                continue
            if local.status != broker.status:
                findings.append(ReconciliationFinding(
                    "STATUS_MISMATCH", broker_id,
                    f"local={local.status} broker={broker.status}",
                ))
            if local.filled_quantity != broker.filled_quantity:
                findings.append(ReconciliationFinding(
                    "FILL_QUANTITY_MISMATCH", broker_id,
                    f"local={local.filled_quantity} broker={broker.filled_quantity}",
                ))

        for broker_id in broker_by_id.keys() - local_by_broker.keys():
            findings.append(ReconciliationFinding(
                "BROKER_MISSING_LOCALLY", broker_id,
                "broker order is absent from local durable state",
            ))

        return ReconciliationReport(tuple(findings))

    def reconcile_positions(
        self,
        local_positions: tuple[BrokerPosition, ...],
        broker_positions: tuple[BrokerPosition, ...],
    ) -> ReconciliationReport:
        def normalize(items: tuple[BrokerPosition, ...]) -> dict[str, BrokerPosition]:
            return {item.instrument_id: item for item in items}

        local = normalize(local_positions)
        broker = normalize(broker_positions)
        findings: list[ReconciliationFinding] = []
        for instrument_id in local.keys() | broker.keys():
            left = local.get(instrument_id)
            right = broker.get(instrument_id)
            if left is None or right is None or left.quantity != right.quantity or left.average_price != right.average_price:
                findings.append(ReconciliationFinding(
                    "POSITION_MISMATCH", instrument_id,
                    f"local={left} broker={right}",
                ))
        return ReconciliationReport(tuple(findings))
