"""Transactional persistence boundary for execution orders and history.

The repository is deliberately provider-neutral. It owns durable client-order
identity, lifecycle persistence, audit history, idempotent fill ingestion, and
point-in-time position projection from persisted fills; broker adapters remain
responsible only for translating normalized requests to provider APIs.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.brokers.contracts import BrokerFill, BrokerPosition
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
    """SQLAlchemy repository with database-backed execution state.

    Callers own the transaction. Methods flush rather than commit so creation,
    risk authorization bookkeeping, lifecycle changes, fills, and projections
    can be composed into a single transaction.
    """

    def __init__(self, session: Session, state_machine: OrderStateMachine | None = None) -> None:
        self.session = session
        self.state_machine = state_machine or OrderStateMachine()

    def get(self, client_order_id: str) -> ExecutionOrder | None:
        return self.session.get(ExecutionOrder, client_order_id)

    def get_by_broker_order_id(self, broker_order_id: str) -> ExecutionOrder | None:
        if not broker_order_id.strip():
            raise ValueError("broker_order_id cannot be empty")
        return self.session.scalar(
            select(ExecutionOrder).where(ExecutionOrder.broker_order_id == broker_order_id)
        )

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

    def ingest_broker_fill(self, fill: BrokerFill, *, source: str) -> ExecutionFill:
        """Resolve a normalized provider fill to its durable order and ingest it.

        Provider fill discovery intentionally does not carry local client-order
        IDs. The durable broker-order mapping is the authoritative join key.
        Unknown broker orders fail closed rather than creating orphan fills.
        """
        order = self.get_by_broker_order_id(fill.broker_order_id)
        if order is None:
            raise KeyError(f"execution order not found for broker order: {fill.broker_order_id}")
        return self.ingest_fill(
            FillIngestRequest(
                broker_fill_id=fill.broker_fill_id,
                client_order_id=order.client_order_id,
                broker_order_id=fill.broker_order_id,
                instrument_id=fill.instrument_id,
                side=fill.side,
                quantity=fill.quantity,
                fill_price=fill.price,
                fee=fill.fee,
                event_time=fill.event_time,
                source=source,
            )
        )

    def ingest_fill(self, request: FillIngestRequest) -> ExecutionFill:
        """Persist one broker fill exactly once and advance order fill state."""
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
        nested = self.session.begin_nested()
        try:
            self.session.add(fill)
            self.session.flush()
        except IntegrityError as exc:
            nested.rollback()
            winner = self.session.get(ExecutionFill, request.broker_fill_id)
            if winner is not None and self._fill_matches(winner, request):
                return winner
            raise IdempotencyConflict("concurrent broker fill ingestion conflict") from exc
        else:
            nested.commit()

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

    def project_positions(self) -> tuple[BrokerPosition, ...]:
        """Project net positions from durable fills in deterministic event order.

        This is a read-only projection: persisted broker fills remain the source
        of truth. A position is represented by signed net quantity and the
        volume-weighted entry price of the remaining open quantity. When a fill
        crosses through flat, the residual quantity starts a new entry price.
        """
        fills = self.session.scalars(
            select(ExecutionFill).order_by(
                ExecutionFill.event_time.asc(), ExecutionFill.broker_fill_id.asc()
            )
        ).all()
        quantities: dict[str, Decimal] = {}
        average_prices: dict[str, Decimal] = {}

        for fill in fills:
            signed_fill = fill.quantity if fill.side == "BUY" else -fill.quantity
            current_quantity = quantities.get(fill.instrument_id, Decimal("0"))
            current_average = average_prices.get(fill.instrument_id, Decimal("0"))
            next_quantity = current_quantity + signed_fill

            if current_quantity == 0 or (current_quantity > 0 and signed_fill > 0) or (
                current_quantity < 0 and signed_fill < 0
            ):
                total_abs = abs(current_quantity) + abs(signed_fill)
                average_prices[fill.instrument_id] = (
                    current_average * abs(current_quantity) + fill.fill_price * abs(signed_fill)
                ) / total_abs
            elif next_quantity == 0:
                average_prices.pop(fill.instrument_id, None)
            elif (current_quantity > 0 and next_quantity > 0) or (
                current_quantity < 0 and next_quantity < 0
            ):
                # Closing part of an existing position does not change its entry price.
                average_prices[fill.instrument_id] = current_average
            else:
                # The fill crossed through flat; its residual opens at this fill price.
                average_prices[fill.instrument_id] = fill.fill_price

            quantities[fill.instrument_id] = next_quantity

        return tuple(
            BrokerPosition(
                instrument_id=instrument_id,
                quantity=quantity,
                average_price=average_prices[instrument_id],
            )
            for instrument_id, quantity in sorted(quantities.items())
            if quantity != 0
        )

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
        broker_order_matches = (
            request.broker_order_id is None
            or row.broker_order_id == request.broker_order_id
        )
        return (
            row.client_order_id == request.client_order_id
            and broker_order_matches
            and row.instrument_id == request.instrument_id
            and row.side == request.side
            and row.quantity == request.quantity
            and row.fill_price == request.fill_price
            and row.fee == request.fee
            and row.event_time == request.event_time.astimezone(timezone.utc)
            and row.source == request.source
        )
