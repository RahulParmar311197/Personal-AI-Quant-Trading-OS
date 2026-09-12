from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.brokers.contracts import BrokerOrderResult, BrokerPosition
from app.execution.lifecycle import (
    DurableOrderKey,
    IdempotencyConflict,
    InvalidOrderTransition,
    OrderIdempotencyStore,
    OrderLifecycleEvent,
    OrderLifecycleState,
    OrderStateMachine,
)
from app.execution.reconciliation import LocalOrderSnapshot, ReconciliationService

NOW = datetime(2026, 1, 2, 10, tzinfo=timezone.utc)


def test_order_state_machine_allows_normal_submission_and_fill() -> None:
    machine = OrderStateMachine()
    state = OrderLifecycleState("ord-1")
    state = machine.apply(state, OrderLifecycleEvent("ord-1", "SUBMITTED", NOW, "br-1"))
    state = machine.apply(state, OrderLifecycleEvent("ord-1", "ACKNOWLEDGED", NOW, "br-1"))
    state = machine.apply(state, OrderLifecycleEvent("ord-1", "FILLED", NOW, "br-1"))
    assert state.status == "FILLED"
    assert machine.is_terminal(state.status)


def test_order_state_machine_allows_unknown_from_created_after_ambiguous_submission() -> None:
    machine = OrderStateMachine()
    state = machine.apply(
        OrderLifecycleState("ord-ambiguous"),
        OrderLifecycleEvent("ord-ambiguous", "UNKNOWN", NOW, message="broker timeout"),
    )
    assert state.status == "UNKNOWN"
    assert state.last_message == "broker timeout"


def test_state_machine_rejects_illegal_transition() -> None:
    with pytest.raises(InvalidOrderTransition):
        OrderStateMachine().apply(
            OrderLifecycleState("ord-1"),
            OrderLifecycleEvent("ord-1", "FILLED", NOW),
        )


def test_state_machine_rejects_out_of_order_events() -> None:
    machine = OrderStateMachine()
    state = machine.apply(
        OrderLifecycleState("ord-1"), OrderLifecycleEvent("ord-1", "SUBMITTED", NOW)
    )
    with pytest.raises(InvalidOrderTransition):
        machine.apply(
            state,
            OrderLifecycleEvent("ord-1", "ACKNOWLEDGED", NOW.replace(hour=9)),
        )


def test_idempotency_is_stable_and_conflicts_are_rejected() -> None:
    store = OrderIdempotencyStore()
    key = DurableOrderKey("ord-1", "strategy-a", NOW)
    assert store.reserve(key) is True
    assert store.reserve(key) is False
    assert store.contains("ord-1")
    with pytest.raises(IdempotencyConflict):
        store.reserve(DurableOrderKey("ord-1", "strategy-b", NOW))


def test_order_reconciliation_is_fail_closed_on_status_or_fill_mismatch() -> None:
    service = ReconciliationService()
    local = LocalOrderSnapshot("ord-1", "br-1", "FILLED", Decimal("10"), Decimal("10"), "NIFTY")
    broker = BrokerOrderResult("br-1", "ord-1", "PARTIALLY_FILLED", Decimal("5"), Decimal("100"))
    report = service.reconcile_orders((local,), (broker,))
    assert not report.healthy
    assert {item.kind for item in report.findings} == {"STATUS_MISMATCH", "FILL_QUANTITY_MISMATCH"}


def test_order_reconciliation_detects_unknown_broker_order() -> None:
    service = ReconciliationService()
    broker = BrokerOrderResult("br-2", "ord-2", "OPEN", Decimal("0"), None)
    report = service.reconcile_orders((), (broker,))
    assert report.findings[0].kind == "BROKER_MISSING_LOCALLY"


def test_position_reconciliation_requires_exact_quantity_and_average_price() -> None:
    service = ReconciliationService()
    left = BrokerPosition("NIFTY", Decimal("10"), Decimal("100"))
    right = BrokerPosition("NIFTY", Decimal("10"), Decimal("101"))
    report = service.reconcile_positions((left,), (right,))
    assert not report.healthy
    assert report.findings[0].kind == "POSITION_MISMATCH"
