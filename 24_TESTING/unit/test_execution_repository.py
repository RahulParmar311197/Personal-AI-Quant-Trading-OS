from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.brokers.contracts import BrokerFill
from app.core.database import Base
from app.execution.lifecycle import DurableOrderKey, IdempotencyConflict, OrderLifecycleEvent
from app.execution.repository import ExecutionOrderRepository
from app.models import ExecutionOrder, Instrument


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


def test_repository_ingests_provider_fill_and_replays_idempotently() -> None:
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
            OrderLifecycleEvent("c1", "SUBMITTED", NOW, broker_order_id="broker-7"),
        )

        fill = BrokerFill(
            broker_fill_id="trade-1",
            broker_order_id="broker-7",
            instrument_id="NIFTY",
            side="BUY",
            quantity=Decimal("4"),
            price=Decimal("100.50"),
            event_time=NOW,
        )
        first = repo.ingest_broker_fill(fill, source="upstox")
        replay = repo.ingest_broker_fill(fill, source="upstox")

        assert first.broker_fill_id == replay.broker_fill_id
        assert repo.get("c1").filled_quantity == Decimal("4")
        assert repo.get("c1").status == "PARTIALLY_FILLED"
        assert len(repo.list_fills("c1")) == 1


def test_repository_rejects_unknown_provider_order_fill() -> None:
    with make_session() as session:
        seed_instrument(session)
        repo = ExecutionOrderRepository(session)
        fill = BrokerFill(
            broker_fill_id="trade-unknown",
            broker_order_id="broker-missing",
            instrument_id="NIFTY",
            side="BUY",
            quantity=Decimal("1"),
            price=Decimal("100"),
            event_time=NOW,
        )
        with pytest.raises(KeyError, match="broker-missing"):
            repo.ingest_broker_fill(fill, source="upstox")


def test_repository_rejects_reused_provider_fill_id_with_different_economics() -> None:
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
            OrderLifecycleEvent("c1", "SUBMITTED", NOW, broker_order_id="broker-7"),
        )
        first = BrokerFill(
            broker_fill_id="trade-1",
            broker_order_id="broker-7",
            instrument_id="NIFTY",
            side="BUY",
            quantity=Decimal("4"),
            price=Decimal("100"),
            event_time=NOW,
        )
        repo.ingest_broker_fill(first, source="upstox")
        conflicting = BrokerFill(
            broker_fill_id="trade-1",
            broker_order_id="broker-7",
            instrument_id="NIFTY",
            side="BUY",
            quantity=Decimal("4"),
            price=Decimal("101"),
            event_time=NOW,
        )
        with pytest.raises(IdempotencyConflict):
            repo.ingest_broker_fill(conflicting, source="upstox")
