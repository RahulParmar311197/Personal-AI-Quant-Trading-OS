from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.execution.lifecycle import DurableOrderKey, IdempotencyConflict, OrderLifecycleEvent
from app.execution.repository import ExecutionOrderRepository
from app.models import Bar, ExecutionOrder, Instrument
from app.core.database import Base


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def seed_instrument(session: Session) -> None:
    session.add(
        Instrument(
            instrument_id="NIFTY",
            exchange="NSE",
            segment="INDEX",
            symbol="NIFTY",
            currency="INR",
            timezone="Asia/Kolkata",
            asset_type="INDEX",
        )
    )
    session.flush()


def test_repository_reserve_is_idempotent() -> None:
    with make_session() as session:
        seed_instrument(session)
        repo = ExecutionOrderRepository(session)
        key = DurableOrderKey("c1", "strategy-a", NOW)
        first = repo.reserve(
            key=key,
            instrument_id="NIFTY",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("2"),
            created_at=NOW,
        )
        second = repo.reserve(
            key=key,
            instrument_id="NIFTY",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("2"),
            created_at=NOW,
        )
        assert first.client_order_id == second.client_order_id
        assert session.query(ExecutionOrder).count() == 1


def test_repository_rejects_same_client_id_for_different_intent() -> None:
    with make_session() as session:
        seed_instrument(session)
        repo = ExecutionOrderRepository(session)
        repo.reserve(
            key=DurableOrderKey("c1", "strategy-a", NOW),
            instrument_id="NIFTY",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("2"),
            created_at=NOW,
        )
        with pytest.raises(IdempotencyConflict):
            repo.reserve(
                key=DurableOrderKey("c1", "strategy-b", NOW),
                instrument_id="NIFTY",
                side="BUY",
                order_type="MARKET",
                quantity=Decimal("2"),
                created_at=NOW,
            )


def test_repository_persists_lifecycle_and_fills() -> None:
    with make_session() as session:
        seed_instrument(session)
        repo = ExecutionOrderRepository(session)
        repo.reserve(
            key=DurableOrderKey("c1", "strategy-a", NOW),
            instrument_id="NIFTY",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("10"),
            created_at=NOW,
        )
        repo.transition(
            "c1",
            OrderLifecycleEvent("c1", "SUBMITTED", NOW),
        )
        repo.transition(
            "c1",
            OrderLifecycleEvent("c1", "PARTIALLY_FILLED", NOW),
            filled_quantity=Decimal("4"),
        )
        row = repo.transition(
            "c1",
            OrderLifecycleEvent("c1", "FILLED", NOW),
            filled_quantity=Decimal("10"),
        )
        session.commit()

        assert row.status == "FILLED"
        assert row.filled_quantity == Decimal("10")


def test_repository_rejects_non_monotonic_fill() -> None:
    with make_session() as session:
        seed_instrument(session)
        repo = ExecutionOrderRepository(session)
        repo.reserve(
            key=DurableOrderKey("c1", "strategy-a", NOW),
            instrument_id="NIFTY",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("10"),
            created_at=NOW,
        )
        repo.transition(
            "c1",
            OrderLifecycleEvent("c1", "SUBMITTED", NOW),
        )
        repo.transition(
            "c1",
            OrderLifecycleEvent("c1", "PARTIALLY_FILLED", NOW),
            filled_quantity=Decimal("6"),
        )
        with pytest.raises(ValueError):
            repo.transition(
                "c1",
                OrderLifecycleEvent("c1", "PARTIALLY_FILLED", NOW),
                filled_quantity=Decimal("5"),
            )
