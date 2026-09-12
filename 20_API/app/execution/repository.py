"""Transactional persistence boundary for execution orders and history.

The repository is deliberately provider-neutral. It owns durable client-order
identity, lifecycle persistence, audit history, and idempotent fill ingestion;
broker adapters remain responsible only for translating normalized requests
to provider APIs.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.execution.history import FillIngestRequest
from app.execution.lifecycle import (
    DurableOrderKey,
    IdempotencyConflict,
    OrderLifecycleEvent,
    OrderLifecycleState,
    OrderStateMachine,
)
from app.models.execution import ExecutionOrder
from app.models.execution_history import ExecutionAuditEvent, ExecutionFill


class OrderAlreadyExists(Exception):
    """Raised when an order identity is already reserved for another intent."""


class ExecutionOrderRepository:
    """SQLAlchemy repository with database-backed idempotency.

    Callers own the transaction. Methods flush rather than commit so creation,
    risk authorization bookkeeping, lifecycle changes, and fills can be
    composed into a single transaction.
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

        created_at_utc = created_at.astimezone(timezone.utc)
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
            created_at=created_at_utc,
            updated_at=created_at_utc,
            last_message="order identity reserved",
        )

        # Establish the SAVEPOINT before the INSERT so an IntegrityError does
        # not invalidate the caller's outer transaction. This is important when
        # execution shares a transaction with risk/audit bookkeeping.
        nested = self.session.begin_nested()
        try:
            self.session.add(row)
            self.session.flush()
        except IntegrityError as exc:
            nested.rollback()
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
                    return winner
            raise OrderAlreadyExists("concurrent order identity reservation conflict") from exc
        else:
            nested.commit()

        self._record_audit(
            client_order_id=row.client_order_id,
            broker_order_id=None,
            from_status=None,
            to_status="CREATED",
            event_time=created_at_utc,
            source="execution.repository",
            message="order identity reserved",
        )
        self.session.flush()
        return row

    def transition(
        self,
        client_order_id: str,
        event: OrderLifecycleEvent,
        *,
        filled_quantity: Decimal | None = None,
        source: str = "execution.repository",
    ) -> ExecutionOrder:
        row = self.get(client_order_id)
        if row is None:
            raise KeyError(f"execution order not found: {client_order_id}")

        previous_status = row.status
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

        self._record_audit(
            client_order_id=row.client_order_id,
            broker_order_id=row.broker_order_id,
            from_status=previous_status,
            to_status=next_state.status,
            event_time=next_state.updated_at or row.updated_at,
            source=source,
            message=next_state.last_message,
        )
        self.session.flush()
        return row

    def ingest_fill(self, request: FillIngestRequest) -> ExecutionFill:
        """Persist one broker fill exactly once and advance order fill state.

        The broker fill ID is the idempotency key. Replaying the exact fill is
        a no-op; reusing the same provider fill ID for different economics is
        rejected. The fill row and order lifecycle update share the caller's
        transaction.
        """
        existing = self.session.get(ExecutionFill, request.broker_fill_id)
        if existing is not None:
            if not self._fill_matches(existing, request):
                raise IdempotencyConflict(
                    "broker_fill_id is already recorded with different fill economics"
                )
            return existing

        order = self.get(request.client_order_id)
        if order is None:
            raise KeyError(f"execution order not found: {request.client_order_id}")
        if order.instrument_id != request.instrument_id or order.side != request.side:
            raise ValueError("fill instrument/side does not match durable order")
        if request.broker_order_id and order.broker_order_id not in (None, request.broker_order_id):
            raise ValueError("fill broker_order_id does not match durable order")

        cumulative = order.filled_quantity + request.quantity
        if cumulative > order.requested_quantity:
            raise ValueError("cumulative fill quantity exceeds requested quantity")

        fill = ExecutionFill(
            broker_fill_id=request.broker_fill_id,
            client_order_id=request.client_order_id,
            broker_order_id=request.broker_order_id or order.broker_order_id,
            instrument_id=request.instrument_id,
            side=request.side,
            quantity=request.quantity,
            fill_price=request.fill_price,
            fee=request.fee,
            event_time=request.event_time.astimezone(timezone.utc),
            recorded_at=datetime.now(timezone.utc),
            source=request.source,
        )
        self.session.add(fill)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            winner = self.session.get(ExecutionFill, request.broker_fill_id)
            if winner is not None and self._fill_matches(winner, request):
                return winner
            raise IdempotencyConflict("concurrent broker fill ingestion conflict") from exc

        next_status = "FILLED" if cumulative == order.requested_quantity else "PARTIALLY_FILLED"
        self.transition(
            request.client_order_id,
            OrderLifecycleEvent(
                client_order_id=request.client_order_id,
                status=next_status,  # type: ignore[arg-type]
                event_time=request.event_time,
                broker_order_id=request.broker_order_id,
                message=f"broker fill {request.broker_fill_id} ingested",
            ),
            filled_quantity=cumulative,
            source=request.source,
        )
        return fill

    def list_audit_events(self, client_order_id: str) -> tuple[ExecutionAuditEvent, ...]:
        rows = self.session.scalars(
            select(ExecutionAuditEvent)
            .where(ExecutionAuditEvent.client_order_id == client_order_id)
            .order_by(ExecutionAuditEvent.event_time.asc(), ExecutionAuditEvent.event_id.asc())
        ).all()
        return tuple(rows)

    def list_fills(self, client_order_id: str) -> tuple[ExecutionFill, ...]:
        rows = self.session.scalars(
            select(ExecutionFill)
            .where(ExecutionFill.client_order_id == client_order_id)
            .order_by(ExecutionFill.event_time.asc(), ExecutionFill.broker_fill_id.asc())
        ).all()
        return tuple(rows)

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

    def _record_audit(
        self,
        *,
        client_order_id: str,
        broker_order_id: str | None,
        from_status: str | None,
        to_status: str,
        event_time: datetime,
        source: str,
        message: str,
    ) -> None:
        self.session.add(
            ExecutionAuditEvent(
                event_id=uuid4().hex,
                client_order_id=client_order_id,
                broker_order_id=broker_order_id,
                from_status=from_status,
                to_status=to_status,
                event_time=event_time.astimezone(timezone.utc),
                recorded_at=datetime.now(timezone.utc),
                source=source,
                message=message,
            )
        )

    @staticmethod
    def _fill_matches(row: ExecutionFill, request: FillIngestRequest) -> bool:
        return (
            row.client_order_id == request.client_order_id
            and row.broker_order_id == request.broker_order_id
            and row.instrument_id == request.instrument_id
            and row.side == request.side
            and row.quantity == request.quantity
            and row.fill_price == request.fill_price
            and row.fee == request.fee
            and row.event_time == request.event_time.astimezone(timezone.utc)
            and row.source == request.source
        )
