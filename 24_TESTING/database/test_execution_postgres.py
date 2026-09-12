"""PostgreSQL integration tests for durable execution persistence.

These tests are intentionally opt-in. CI supplies TEST_DATABASE_URL through its
PostgreSQL service; local developers may point the same variable at a disposable
PostgreSQL database.
"""

import os
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.execution.history import FillIngestRequest
from app.execution.lifecycle import DurableOrderKey, IdempotencyConflict, OrderLifecycleEvent
from app.execution.repository import ExecutionOrderRepository
from app.models import ExecutionFill, ExecutionOrder, Instrument

DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="TEST_DATABASE_URL is required for PostgreSQL integration tests",
)

NOW = datetime(2026, 9, 12, 9, 15, tzinfo=timezone.utc)


def seed_instrument(session: Session, instrument_id: str = "NIFTY-POSTGRES") -> None:
    session.add(
        Instrument(
            instrument_id=instrument_id,
            exchange="NSE",
            segment="INDEX",
            symbol=instrument_id,
            currency="INR",
            timezone="Asia/Kolkata",
            asset_type="INDEX",
        )
    )
    session.flush()


def make_engine():
    assert DATABASE_URL is not None
    return create_engine(DATABASE_URL, pool_pre_ping=True)


def test_postgres_schema_contains_execution_constraints() -> None:
    engine = make_engine()
    with engine.connect() as connection:
        tables = connection.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        ).scalars().all()
        assert "instruments" in tables
        assert "execution_orders" in tables
        assert "execution_audit_events" in tables
        assert "execution_fills" in tables

        constraints = connection.execute(
            text(
                "SELECT constraint_name FROM information_schema.table_constraints "
                "WHERE table_schema = 'public' AND table_name = 'execution_orders'"
            )
        ).scalars().all()
        assert "uq_execution_signal_identity" in constraints
        assert "ck_execution_status" in constraints


def test_postgres_reservation_is_idempotent_and_preserves_outer_transaction() -> None:
    engine = make_engine()
    with Session(engine) as session:
        with session.begin():
            instrument_id = "NIFTY-POSTGRES-IDEMPOTENT"
            seed_instrument(session, instrument_id)
            repo = ExecutionOrderRepository(session)
            key = DurableOrderKey("pg-c1", "strategy-a", NOW)
            first = repo.reserve(
                key=key,
                instrument_id=instrument_id,
                side="BUY",
                order_type="MARKET",
                quantity=Decimal("2"),
                created_at=NOW,
            )
            second = repo.reserve(
                key=key,
                instrument_id=instrument_id,
                side="BUY",
                order_type="MARKET",
                quantity=Decimal("2"),
                created_at=NOW,
            )
            assert first.client_order_id == second.client_order_id

            session.add(
                Instrument(
                    instrument_id="OUTER-TX-POSTGRES",
                    exchange="NSE",
                    segment="INDEX",
                    symbol="OUTER-TX-POSTGRES",
                    currency="INR",
                    timezone="Asia/Kolkata",
                    asset_type="INDEX",
                )
            )
            session.flush()

        with Session(engine) as verify:
            assert verify.get(ExecutionOrder, "pg-c1") is not None
            assert verify.get(Instrument, "OUTER-TX-POSTGRES") is not None


def test_postgres_conflicting_client_id_is_rejected() -> None:
    engine = make_engine()
    with Session(engine) as session:
        with session.begin():
            instrument_id = "NIFTY-POSTGRES-CONFLICT"
            seed_instrument(session, instrument_id)
            repo = ExecutionOrderRepository(session)
            repo.reserve(
                key=DurableOrderKey("pg-conflict", "strategy-a", NOW),
                instrument_id=instrument_id,
                side="BUY",
                order_type="MARKET",
                quantity=Decimal("2"),
                created_at=NOW,
            )
            with pytest.raises(IdempotencyConflict):
                repo.reserve(
                    key=DurableOrderKey("pg-conflict", "strategy-b", NOW),
                    instrument_id=instrument_id,
                    side="BUY",
                    order_type="MARKET",
                    quantity=Decimal("2"),
                    created_at=NOW,
                )


def test_postgres_lifecycle_and_monotonic_fill_persist() -> None:
    engine = make_engine()
    with Session(engine) as session:
        with session.begin():
            instrument_id = "NIFTY-POSTGRES-LIFECYCLE"
            seed_instrument(session, instrument_id)
            repo = ExecutionOrderRepository(session)
            repo.reserve(
                key=DurableOrderKey("pg-life", "strategy-a", NOW),
                instrument_id=instrument_id,
                side="BUY",
                order_type="MARKET",
                quantity=Decimal("10"),
                created_at=NOW,
            )
            repo.transition("pg-life", OrderLifecycleEvent("pg-life", "SUBMITTED", NOW))
            repo.transition(
                "pg-life",
                OrderLifecycleEvent("pg-life", "PARTIALLY_FILLED", NOW),
                filled_quantity=Decimal("4"),
            )
            repo.transition(
                "pg-life",
                OrderLifecycleEvent("pg-life", "FILLED", NOW),
                filled_quantity=Decimal("10"),
            )

    with Session(engine) as verify:
        row = verify.get(ExecutionOrder, "pg-life")
        assert row is not None
        assert row.status == "FILLED"
        assert row.filled_quantity == Decimal("10.00000000")
        audit = verify.scalars(
            text("SELECT event_id FROM execution_audit_events WHERE client_order_id = 'pg-life'")
        ).all()
        assert len(audit) == 4


def test_postgres_fill_ingestion_is_idempotent_and_updates_lifecycle() -> None:
    engine = make_engine()
    with Session(engine) as session:
        with session.begin():
            instrument_id = "NIFTY-POSTGRES-FILL"
            seed_instrument(session, instrument_id)
            repo = ExecutionOrderRepository(session)
            repo.reserve(
                key=DurableOrderKey("pg-fill", "strategy-a", NOW),
                instrument_id=instrument_id,
                side="BUY",
                order_type="MARKET",
                quantity=Decimal("10"),
                created_at=NOW,
            )
            repo.transition("pg-fill", OrderLifecycleEvent("pg-fill", "SUBMITTED", NOW))
            request = FillIngestRequest(
                broker_fill_id="fill-1",
                client_order_id="pg-fill",
                broker_order_id="broker-1",
                instrument_id=instrument_id,
                side="BUY",
                quantity=Decimal("4"),
                fill_price=Decimal("100.25"),
                fee=Decimal("1.10"),
                event_time=NOW,
                source="upstox.sandbox",
            )
            first = repo.ingest_fill(request)
            second = repo.ingest_fill(request)
            assert first.broker_fill_id == second.broker_fill_id

    with Session(engine) as verify:
        row = verify.get(ExecutionOrder, "pg-fill")
        assert row is not None
        assert row.status == "PARTIALLY_FILLED"
        assert row.filled_quantity == Decimal("4.00000000")
        assert verify.get(ExecutionFill, "fill-1") is not None
        assert len(verify.scalars(text("SELECT broker_fill_id FROM execution_fills WHERE client_order_id = 'pg-fill'")).all()) == 1
        assert len(verify.scalars(text("SELECT event_id FROM execution_audit_events WHERE client_order_id = 'pg-fill'")).all()) == 3

        with pytest.raises(IdempotencyConflict):
            # Same provider fill ID with different economics must never mutate history.
            request = FillIngestRequest(
                broker_fill_id="fill-1",
                client_order_id="pg-fill",
                broker_order_id="broker-1",
                instrument_id="NIFTY-POSTGRES-FILL",
                side="BUY",
                quantity=Decimal("5"),
                fill_price=Decimal("100.25"),
                fee=Decimal("1.10"),
                event_time=NOW,
                source="upstox.sandbox",
            )
            ExecutionOrderRepository(verify).ingest_fill(request)
