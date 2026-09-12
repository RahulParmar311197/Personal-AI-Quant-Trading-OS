from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.brokers.contracts import (
    BrokerAccount,
    BrokerCapabilities,
    BrokerOrderResult,
)
from app.execution.reconciliation_runner import ReconciliationRunner


@dataclass
class FakeRow:
    client_order_id: str
    broker_order_id: str
    status: str
    requested_quantity: Decimal
    filled_quantity: Decimal
    instrument_id: str


class FakeRepository:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def find_active(self):
        return self.rows


class FakeBroker:
    def __init__(self, orders, healthy=True):
        self.orders = tuple(orders)
        self.healthy = healthy
        self.capabilities = BrokerCapabilities(list_orders=True)
        self.list_calls = 0

    def healthcheck(self):
        return self.healthy

    def list_orders(self):
        self.list_calls += 1
        return self.orders

    def get_order(self, broker_order_id):
        raise AssertionError("targeted get_order must not be used when list_orders is supported")


def order(client_id, broker_id, status="FILLED", quantity=Decimal("1"), filled=Decimal("1")):
    return BrokerOrderResult(broker_id, client_id, status, filled, Decimal("100"), "")


def test_runner_uses_full_broker_order_snapshot():
    row = FakeRow("client-1", "UP-1", "FILLED", Decimal("1"), Decimal("1"), "NSE_EQ|ABC")
    broker = FakeBroker([order("client-1", "UP-1")])
    result = ReconciliationRunner(FakeRepository([row]), broker).run()
    assert result.healthy
    assert broker.list_calls == 1


def test_runner_detects_broker_only_order():
    row = FakeRow("client-1", "UP-1", "FILLED", Decimal("1"), Decimal("1"), "NSE_EQ|ABC")
    broker = FakeBroker([order("client-1", "UP-1"), order("foreign", "UP-2", "OPEN", Decimal("2"), Decimal("0"))])
    result = ReconciliationRunner(FakeRepository([row]), broker).run()
    assert not result.healthy
    assert any(f.kind == "BROKER_MISSING_LOCALLY" for f in result.report.findings)


def test_runner_fails_closed_when_broker_unavailable():
    broker = FakeBroker([], healthy=False)
    result = ReconciliationRunner(FakeRepository([]), broker).run()
    assert not result.healthy
    assert result.report.findings[0].kind == "BROKER_UNAVAILABLE"
