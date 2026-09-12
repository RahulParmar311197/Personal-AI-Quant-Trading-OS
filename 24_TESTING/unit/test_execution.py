from datetime import datetime, timezone
from decimal import Decimal

from app.brokers.contracts import BrokerAccount, BrokerCapabilities, BrokerAdapter, BrokerOrderRequest, BrokerOrderResult
from app.execution.engine import ExecutionEngine, ExecutionIntent
from app.risk.engine import RiskDecision


class FakeBroker(BrokerAdapter):
    def __init__(self) -> None:
        self.calls = 0

    @property
    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities()

    def place_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        self.calls += 1
        return BrokerOrderResult("broker-1", request.client_order_id, "PENDING", Decimal("0"), None)

    def cancel_order(self, broker_order_id: str) -> BrokerOrderResult:
        raise NotImplementedError

    def get_order(self, broker_order_id: str) -> BrokerOrderResult:
        raise NotImplementedError

    def get_account(self) -> BrokerAccount:
        raise NotImplementedError

    def get_positions(self):
        raise NotImplementedError

    def healthcheck(self) -> bool:
        return True


def risk_allowed() -> RiskDecision:
    return RiskDecision(
        datetime(2026, 1, 1, tzinfo=timezone.utc), True, "LONG", Decimal("10"), Decimal("100"), Decimal("1000"), ()
    )


def test_execution_blocks_when_live_disabled() -> None:
    broker = FakeBroker()
    engine = ExecutionEngine(broker, live_enabled=False)
    result = engine.execute(
        ExecutionIntent("c1", "NIFTY", "BUY", datetime(2026, 1, 1, tzinfo=timezone.utc)),
        risk_allowed(),
        Decimal("2"),
    )
    assert not result.accepted
    assert broker.calls == 0


def test_execution_requires_risk_authorization() -> None:
    broker = FakeBroker()
    engine = ExecutionEngine(broker, live_enabled=True)
    denied = RiskDecision(datetime(2026, 1, 1, tzinfo=timezone.utc), False, "LONG", Decimal("0"), Decimal("0"), Decimal("0"), ("denied",))
    result = engine.execute(
        ExecutionIntent("c1", "NIFTY", "BUY", datetime(2026, 1, 1, tzinfo=timezone.utc)), denied, Decimal("1")
    )
    assert not result.accepted
    assert broker.calls == 0


def test_execution_rejects_duplicate_client_id() -> None:
    broker = FakeBroker()
    engine = ExecutionEngine(broker, live_enabled=True)
    intent = ExecutionIntent("c1", "NIFTY", "BUY", datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert engine.execute(intent, risk_allowed(), Decimal("2")).accepted
    result = engine.execute(intent, risk_allowed(), Decimal("2"))
    assert not result.accepted
    assert broker.calls == 1
