"""Provider-neutral order lifecycle and durable execution contracts."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

ExecutionOrderStatus = Literal[
    "CREATED",
    "SUBMITTED",
    "ACKNOWLEDGED",
    "PARTIALLY_FILLED",
    "FILLED",
    "CANCEL_PENDING",
    "CANCELLED",
    "REJECTED",
    "UNKNOWN",
    "RECONCILED",
    "FAILED",
]

_TERMINAL = {"FILLED", "CANCELLED", "REJECTED", "FAILED", "RECONCILED"}
_TRANSITIONS: dict[ExecutionOrderStatus, frozenset[ExecutionOrderStatus]] = {
    "CREATED": frozenset({"SUBMITTED", "FAILED"}),
    "SUBMITTED": frozenset({"ACKNOWLEDGED", "PARTIALLY_FILLED", "FILLED", "REJECTED", "UNKNOWN", "FAILED"}),
    "ACKNOWLEDGED": frozenset({"PARTIALLY_FILLED", "FILLED", "CANCEL_PENDING", "REJECTED", "UNKNOWN", "FAILED"}),
    "PARTIALLY_FILLED": frozenset({"PARTIALLY_FILLED", "FILLED", "CANCEL_PENDING", "UNKNOWN", "FAILED"}),
    "FILLED": frozenset({"RECONCILED"}),
    "CANCEL_PENDING": frozenset({"CANCELLED", "PARTIALLY_FILLED", "FILLED", "UNKNOWN", "FAILED"}),
    "CANCELLED": frozenset({"RECONCILED"}),
    "REJECTED": frozenset({"RECONCILED"}),
    "UNKNOWN": frozenset({"ACKNOWLEDGED", "PARTIALLY_FILLED", "FILLED", "CANCELLED", "REJECTED", "RECONCILED", "FAILED"}),
    "RECONCILED": frozenset(),
    "FAILED": frozenset(),
}


@dataclass(frozen=True)
class OrderLifecycleEvent:
    client_order_id: str
    status: ExecutionOrderStatus
    event_time: datetime
    broker_order_id: str | None = None
    message: str = ""

    def __post_init__(self) -> None:
        if not self.client_order_id.strip():
            raise ValueError("client_order_id cannot be empty")
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")


@dataclass(frozen=True)
class OrderLifecycleState:
    client_order_id: str
    status: ExecutionOrderStatus = "CREATED"
    broker_order_id: str | None = None
    updated_at: datetime | None = None
    last_message: str = ""


class InvalidOrderTransition(ValueError):
    """Raised when an order lifecycle transition violates the state machine."""


class OrderStateMachine:
    """Deterministic state machine; persistence is supplied by the caller."""

    def apply(self, state: OrderLifecycleState, event: OrderLifecycleEvent) -> OrderLifecycleState:
        if event.client_order_id != state.client_order_id:
            raise InvalidOrderTransition("event client_order_id does not match state")
        if state.updated_at is not None and event.event_time < state.updated_at:
            raise InvalidOrderTransition("out-of-order lifecycle event")
        if event.status != state.status and event.status not in _TRANSITIONS[state.status]:
            raise InvalidOrderTransition(f"invalid transition {state.status} -> {event.status}")
        return OrderLifecycleState(
            client_order_id=state.client_order_id,
            status=event.status,
            broker_order_id=event.broker_order_id or state.broker_order_id,
            updated_at=event.event_time.astimezone(timezone.utc),
            last_message=event.message,
        )

    @staticmethod
    def is_terminal(status: ExecutionOrderStatus) -> bool:
        return status in _TERMINAL


@dataclass(frozen=True)
class DurableOrderKey:
    client_order_id: str
    strategy_id: str
    signal_event_time: datetime

    def __post_init__(self) -> None:
        if not self.client_order_id.strip() or not self.strategy_id.strip():
            raise ValueError("durable order identity cannot be empty")
        if self.signal_event_time.tzinfo is None:
            raise ValueError("signal_event_time must be timezone-aware")


class IdempotencyConflict(ValueError):
    """Raised when one client order ID is reused for a different order intent."""


class OrderIdempotencyStore:
    """Small repository protocol used by execution orchestration.

    Production implementations must persist this identity with a unique
    database constraint. The in-memory implementation is intentionally useful
    only for deterministic unit tests and local development.
    """

    def __init__(self) -> None:
        self._records: dict[str, DurableOrderKey] = {}

    def reserve(self, key: DurableOrderKey) -> bool:
        existing = self._records.get(key.client_order_id)
        if existing is not None and existing != key:
            raise IdempotencyConflict("client_order_id already belongs to another order intent")
        if existing is not None:
            return False
        self._records[key.client_order_id] = key
        return True

    def contains(self, client_order_id: str) -> bool:
        return client_order_id in self._records
