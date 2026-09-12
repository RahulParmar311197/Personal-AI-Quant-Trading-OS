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

from app.execution.lifecycle import DurableOrderKey, IdempotencyConflict, OrderLifecycleEvent
from app.execution.repository import ExecutionOrderRepository
from app.models import ExecutionOrder, Instrument

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
