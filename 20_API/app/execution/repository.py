"""Transactional persistence boundary for execution orders.

The repository is deliberately provider-neutral. It owns durable client-order
identity and lifecycle persistence; broker adapters remain responsible only
for translating normalized requests to provider APIs.
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.execution.lifecycle import (
    DurableOrderKey,
    IdempotencyConflict,
    OrderLifecycleEvent,
    OrderLifecycleState,
    OrderStateMachine,
)
from app.models.execution import ExecutionOrder


class OrderAlreadyExists(Exception):
    """Raised when an order identity is already reserved for another intent."""


class ExecutionOrderRepository:
    """SQLAlchemy repository with database-backed idempotency.

    Callers own the transaction. Methods flush rather than commit so creation,
    risk authorization bookkeeping, and lifecycle changes can be composed into
    a single transaction when appropriate.
    """

    def __init__(self, session: Session, state_machine: OrderStateMachine | None = None) -> None:
        self.session = session
        self.state_machine = state_machine or OrderStateMachine()

    def get(self, client_order_id: str) -> ExecutionOrder | None:
        return self.session.get(ExecutionOrder, client_order_id)

    def reserve(
        self,
        *,
        key: DurableOrderKey,
        instrument_id: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        created_at: datetime,
    ) -> ExecutionOrder:
        existing = self.get(key.client_order_id)
        if existing is not None:
            if (
                existing.strategy_id != key.strategy_id
                or existing.signal_event_time != key.signal_event_time
                or existing.instrument_id != instrument_id
                or existing.side != side
                or existing.order_type != order_type
                or existing.requested_quantity != quantity
            ):
                raise IdempotencyConflict(
                    "client_order_id is already reserved for a different order intent"
                )
            return existing

        row = ExecutionOrder(
            client_order_id=key.client_order_id,
            strategy_id=key.strategy_id,
            instrument_id=instrument_id,
            side=side,
            order_type=order_type,
            requested_quantity=quantity,
            filled_quantity=Decimal("0"),
            status="CREATED",
            signal_event_time=key.signal_event_time.astimezone(timezone.utc),
            created_at=created_at.astimezone(timezone.utc),
            updated_at=created_at.astimezone(timezone.utc),
            last_message="order identity reserved",
        )
        self.session.add(row)
        try:
            self.session.flush()
        except IntegrityError as exc:
            # A duplicate reservation is isolated to a SAVEPOINT. Rolling back
            # the caller's whole transaction here could discard unrelated risk
            # or audit writes that are meant to commit atomically with execution.
            nested = self.session.begin_nested()
            try:
                winner = self.get(key.client_order_id)
                if winner is not None:
                    if (
                        winner.strategy_id == key.strategy_id
                        and winner.signal_event_time == key.signal_event_time
                        and winner.instrument_id == instrument_id
                        and winner.side == side
                        and winner.order_type == order_type
                        and winner.requested_quantity == quantity
                    ):
                        nested.commit()
                        return winner
            finally:
                if nested.is_active:
                    nested.rollback()
            raise OrderAlreadyExists("concurrent order identity reservation conflict") from exc
        return row

    def transition(
        self,
        client_order_id: str,
        event: OrderLifecycleEvent,
        *,
        filled_quantity: Decimal | None = None,
    ) -> ExecutionOrder:
        row = self.get(client_order_id)
        if row is None:
            raise KeyError(f"execution order not found: {client_order_id}")

        state = OrderLifecycleState(
            client_order_id=row.client_order_id,
            status=row.status,  # type: ignore[arg-type]
            broker_order_id=row.broker_order_id,
            updated_at=row.updated_at,
            last_message=row.last_message,
        )
        next_state = self.state_machine.apply(state, event)
        row.status = next_state.status
        row.broker_order_id = next_state.broker_order_id
        row.updated_at = next_state.updated_at or row.updated_at
        row.last_message = next_state.last_message

        if filled_quantity is not None:
            if filled_quantity < row.filled_quantity or filled_quantity > row.requested_quantity:
                raise ValueError("filled_quantity must be monotonic and within requested quantity")
            row.filled_quantity = filled_quantity

        self.session.flush()
        return row

    def find_active(self) -> tuple[ExecutionOrder, ...]:
        rows = self.session.scalars(
            select(ExecutionOrder).where(
                ExecutionOrder.status.not_in(("RECONCILED", "FAILED", "CANCELLED", "REJECTED"))
            )
        ).all()
        return tuple(rows)

    def identity_key(self, row: ExecutionOrder) -> DurableOrderKey:
        return DurableOrderKey(
            client_order_id=row.client_order_id,
            strategy_id=row.strategy_id,
            signal_event_time=row.signal_event_time,
        )
