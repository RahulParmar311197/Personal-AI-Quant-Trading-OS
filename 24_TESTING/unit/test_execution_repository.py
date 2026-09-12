from datetime import datetime, timedelta, timezone
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
            instrument_id="NIFTY", exchange="NSE", segment="INDEX", symbol="NIFTY",
            currency="INR", timezone="Asia/Kolkata", asset_type="INDEX",
        )
    )
    session.flush()


def reserve(repo: ExecutionOrderRepository, client_id: str, signal_time: datetime, side: str = "BUY", quantity: str = "10") -> None:
    repo.reserve(
        key=DurableOrderKey(client_id, "strategy-a", signal_time),
        instrument_id="NIFTY", side=side, order_type="MARKET",
        quantity=Decimal(quantity), created_at=signal_time,
    )


def submit(repo: ExecutionOrderRepository, client_id: str, broker_id: str, event_time: datetime) -> None:
    repo.transition(
        client_id,
        OrderLifecycleEvent(client_id, "SUBMITTED", event_time, broker_order_id=broker_id),
    )


def test_repository_reserve_is_idempotent() -> None:
    with make_session() as session:
        seed_instrument(session)
        repo = ExecutionOrderRepository(session)
        first = repo.reserve(key=DurableOrderKey("c1", "strategy-a", NOW), instrument_id="NIFTY", side="BUY", order_type="MARKET", quantity=Decimal("2"), created_at=NOW)
        second = repo.reserve(key=DurableOrderKey("c1", "strategy-a", NOW), instrument_id="NIFTY", side="BUY", order_type="MARKET", quantity=Decimal("2"), created_at=NOW)
        assert first.client_order_id == second.client_order_id
        assert session.query(ExecutionOrder).count() == 1


def test_repository_rejects_same_client_id_for_different_intent() -> None:
    with make_session() as session:
        seed_instrument(session)
        repo = ExecutionOrderRepository(session)
        reserve(repo, "c1", NOW, quantity="2")
        with pytest.raises(IdempotencyConflict):
            reserve(repo, "c1", NOW, side="SELL", quantity="2")


def test_repository_persists_lifecycle_and_fills() -> None:
    with make_session() as session:
        seed_instrument(session)
        repo = ExecutionOrderRepository(session)
        reserve(repo, "c1", NOW)
        submit(repo, "c1", "broker-1", NOW)
        repo.transition("c1", OrderLifecycleEvent("c1", "PARTIALLY_FILLED", NOW), filled_quantity=Decimal("4"))
        row = repo.transition("c1", OrderLifecycleEvent("c1", "FILLED", NOW), filled_quantity=Decimal("10"))
        assert row.status == "FILLED"
        assert row.filled_quantity == Decimal("10")


def test_repository_rejects_non_monotonic_fill() -> None:
    with make_session() as session:
        seed_instrument(session)
        repo = ExecutionOrderRepository(session)
        reserve(repo, "c1", NOW)
        submit(repo, "c1", "broker-1", NOW)
        repo.transition("c1", OrderLifecycleEvent("c1", "PARTIALLY_FILLED", NOW), filled_quantity=Decimal("6"))
        with pytest.raises(ValueError):
            repo.transition("c1", OrderLifecycleEvent("c1", "PARTIALLY_FILLED", NOW), filled_quantity=Decimal("5"))


def test_repository_ingests_provider_fill_and_replays_idempotently() -> None:
    with make_session() as session:
        seed_instrument(session)
        repo = ExecutionOrderRepository(session)
        reserve(repo, "c1", NOW)
        submit(repo, "c1", "broker-7", NOW)
        fill = BrokerFill("trade-1", "broker-7", "NIFTY", "BUY", Decimal("4"), Decimal("100.50"), NOW)
        first = repo.ingest_broker_fill(fill, source="upstox")
        replay = repo.ingest_broker_fill(fill, source="upstox")
        assert first.broker_fill_id == replay.broker_fill_id
        assert repo.get("c1").filled_quantity == Decimal("4")
        assert repo.get("c1").status == "PARTIALLY_FILLED"
        assert len(repo.list_fills("c1")) == 1


def test_repository_projects_net_position_from_durable_fills() -> None:
    with make_session() as session:
        seed_instrument(session)
        repo = ExecutionOrderRepository(session)
        events = (
            ("buy-1", "broker-1", "BUY", "10", "100"),
            ("sell-1", "broker-2", "SELL", "4", "110"),
            ("buy-2", "broker-3", "BUY", "6", "120"),
        )
        for index, (client_id, broker_id, side, quantity, price) in enumerate(events):
            event_time = NOW + timedelta(minutes=index)
            reserve(repo, client_id, event_time, side=side, quantity=quantity)
            submit(repo, client_id, broker_id, event_time)
            repo.ingest_broker_fill(
                BrokerFill(client_id + "-fill", broker_id, "NIFTY", side, Decimal(quantity), Decimal(price), event_time),
                source="test",
            )
        positions = repo.project_positions()
        assert len(positions) == 1
        assert positions[0].instrument_id == "NIFTY"
        assert positions[0].quantity == Decimal("12")
        assert positions[0].average_price == Decimal("110")


def test_repository_rejects_unknown_provider_order_fill() -> None:
    with make_session() as session:
        seed_instrument(session)
        repo = ExecutionOrderRepository(session)
        fill = BrokerFill("trade-unknown", "broker-missing", "NIFTY", "BUY", Decimal("1"), Decimal("100"), NOW)
        with pytest.raises(KeyError, match="broker-missing"):
            repo.ingest_broker_fill(fill, source="upstox")


def test_repository_rejects_reused_provider_fill_id_with_different_economics() -> None:
    with make_session() as session:
        seed_instrument(session)
        repo = ExecutionOrderRepository(session)
        reserve(repo, "c1", NOW)
        submit(repo, "c1", "broker-7", NOW)
        first = BrokerFill("trade-1", "broker-7", "NIFTY", "BUY", Decimal("4"), Decimal("100"), NOW)
        repo.ingest_broker_fill(first, source="upstox")
        conflicting = BrokerFill("trade-1", "broker-7", "NIFTY", "BUY", Decimal("4"), Decimal("101"), NOW)
        with pytest.raises(IdempotencyConflict):
            repo.ingest_broker_fill(conflicting, source="upstox")
