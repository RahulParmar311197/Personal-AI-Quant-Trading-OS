from datetime import datetime, timezone
from decimal import Decimal

from app.brokers.contracts import BrokerAccount, BrokerCapabilities, BrokerAdapter, BrokerOrderRequest, BrokerOrderResult
from app.execution.engine import ExecutionEngine, ExecutionIntent
from app.risk.engine import RiskDecision


class FakeBroker(BrokerAdapter):
    def __init__(self, *, health: bool = True, raise_on_place: bool = False) -> None:
        self.calls = 0
        self.health = health
        self.raise_on_place = raise_on_place

    @property
    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities()

    def place_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        self.calls += 1
        if self.raise_on_place:
            raise TimeoutError("broker response timeout")
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
        return self.health


class FailingTransitionRepository:
    def __init__(self) -> None:
        self.reserved = False

    def get(self, client_order_id: str):
        return None

    def reserve(self, **kwargs) -> None:
        self.reserved = True

    def transition(self, *args, **kwargs) -> None:
        raise RuntimeError("database unavailable")


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


def test_execution_fail_closes_when_healthcheck_raises() -> None:
    broker = FakeBroker()
    broker.healthcheck = lambda: (_ for _ in ()).throw(RuntimeError("healthcheck failed"))
    engine = ExecutionEngine(broker, live_enabled=True)
    result = engine.execute(
        ExecutionIntent("c2", "NIFTY", "BUY", datetime(2026, 1, 1, tzinfo=timezone.utc)),
        risk_allowed(),
        Decimal("1"),
    )
    assert not result.accepted
    assert result.reason == "broker healthcheck failed"
    assert broker.calls == 0


def test_execution_marks_ambiguous_when_broker_call_raises() -> None:
    broker = FakeBroker(raise_on_place=True)
    engine = ExecutionEngine(broker, live_enabled=True)
    result = engine.execute(
        ExecutionIntent("c3", "NIFTY", "BUY", datetime(2026, 1, 1, tzinfo=timezone.utc)),
        risk_allowed(),
        Decimal("1"),
    )
    assert not result.accepted
    assert result.reason == "ambiguous broker response; reconciliation required"
    assert broker.calls == 1


def test_execution_fail_closes_when_durable_acknowledgement_fails() -> None:
    broker = FakeBroker()
    repository = FailingTransitionRepository()
    engine = ExecutionEngine(broker, live_enabled=True, repository=repository)
    result = engine.execute(
        ExecutionIntent("c4", "NIFTY", "BUY", datetime(2026, 1, 1, tzinfo=timezone.utc)),
        risk_allowed(),
        Decimal("1"),
    )
    assert not result.accepted
    assert result.broker_result is not None
    assert result.reason == "broker order accepted; reconciliation required"
    assert repository.reserved
    assert broker.calls == 1
