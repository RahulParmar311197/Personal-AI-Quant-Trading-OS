from dataclasses import dataclass
from decimal import Decimal

from app.brokers.contracts import BrokerCapabilities, BrokerOrderResult, BrokerPosition
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
    def __init__(self, rows, positions=()):
        self.rows = tuple(rows)
        self.positions = tuple(positions)

    def find_active(self):
        return self.rows

    def project_positions(self):
        return self.positions


class FakeBroker:
    def __init__(self, orders, positions=(), healthy=True):
        self.orders = tuple(orders)
        self.positions = tuple(positions)
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

    def get_positions(self):
        return self.positions


def order(client_id, broker_id, status="FILLED", filled=Decimal("1")):
    return BrokerOrderResult(broker_id, client_id, status, filled, Decimal("100"), "")


def position(instrument_id="NSE_EQ|ABC", quantity=Decimal("1"), price=Decimal("100")):
    return BrokerPosition(instrument_id, quantity, price)


def test_runner_uses_full_broker_order_snapshot():
    row = FakeRow("client-1", "UP-1", "FILLED", Decimal("1"), Decimal("1"), "NSE_EQ|ABC")
    broker = FakeBroker([order("client-1", "UP-1")], [position()])
    result = ReconciliationRunner(FakeRepository([row], [position()]), broker).run()
    assert result.healthy
    assert broker.list_calls == 1


def test_runner_detects_broker_only_order():
    row = FakeRow("client-1", "UP-1", "FILLED", Decimal("1"), Decimal("1"), "NSE_EQ|ABC")
    broker = FakeBroker([order("client-1", "UP-1"), order("foreign", "UP-2", "OPEN", Decimal("0"))])
    result = ReconciliationRunner(FakeRepository([row]), broker).run()
    assert not result.healthy
    assert any(f.kind == "BROKER_MISSING_LOCALLY" for f in result.report.findings)


def test_runner_detects_position_mismatch():
    row = FakeRow("client-1", "UP-1", "FILLED", Decimal("1"), Decimal("1"), "NSE_EQ|ABC")
    broker = FakeBroker([order("client-1", "UP-1")], [position(quantity=Decimal("2"))])
    result = ReconciliationRunner(FakeRepository([row], [position()]), broker).run()
    assert not result.healthy
    assert any(f.kind == "POSITION_MISMATCH" for f in result.report.findings)


def test_runner_fails_closed_when_broker_unavailable():
    broker = FakeBroker([], healthy=False)
    result = ReconciliationRunner(FakeRepository([]), broker).run()
    assert not result.healthy
    assert result.report.findings[0].kind == "BROKER_UNAVAILABLE"


def test_runner_fails_closed_when_snapshot_read_fails():
    class BrokenBroker(FakeBroker):
        def list_orders(self):
            raise RuntimeError("timeout")

    broker = BrokenBroker([])
    result = ReconciliationRunner(FakeRepository([]), broker).run()
    assert not result.healthy
    assert result.report.findings[0].kind == "BROKER_UNAVAILABLE"


def test_runner_fails_closed_when_local_position_projection_fails():
    class BrokenRepository(FakeRepository):
        def project_positions(self):
            raise RuntimeError("database unavailable")

    broker = FakeBroker([])
    result = ReconciliationRunner(BrokenRepository([]), broker).run()
    assert not result.healthy
    assert result.report.findings[0].kind == "LOCAL_STATE_UNAVAILABLE"
