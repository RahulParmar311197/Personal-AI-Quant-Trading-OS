from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.risk.engine import RiskConfig, RiskEngine, RiskRequest

UTC = timezone.utc
NOW = datetime(2026, 1, 1, 9, 30, tzinfo=UTC)


def request(**overrides: object) -> RiskRequest:
    values: dict[str, object] = {
        "event_time": NOW,
        "action": "LONG",
        "entry_price": Decimal("100"),
        "stop_price": Decimal("98"),
        "account_equity": Decimal("100000"),
        "daily_realized_pnl": Decimal("0"),
    }
    values.update(overrides)
    return RiskRequest(**values)


def test_risk_engine_sizes_from_risk_and_stop_distance() -> None:
    result = RiskEngine().evaluate(request())
    assert result.allowed is True
    assert result.quantity == Decimal("500")
    assert result.risk_amount == Decimal("1000")


def test_kill_switch_denies() -> None:
    result = RiskEngine().evaluate(request(kill_switch=True))
    assert result.allowed is False
    assert result.quantity == Decimal("0")


def test_daily_loss_limit_denies() -> None:
    result = RiskEngine().evaluate(request(daily_realized_pnl=Decimal("-3000")))
    assert result.allowed is False


def test_open_position_limit_denies() -> None:
    result = RiskEngine().evaluate(request(open_positions=1))
    assert result.allowed is False


def test_stop_distance_limits_are_enforced() -> None:
    engine = RiskEngine()
    assert not engine.evaluate(request(stop_price=Decimal("99.95"))).allowed
    assert not engine.evaluate(request(stop_price=Decimal("90"))).allowed


def test_requested_quantity_is_capped() -> None:
    result = RiskEngine().evaluate(request(requested_quantity=Decimal("100")))
    assert result.allowed is True
    assert result.quantity == Decimal("100")


def test_current_notional_reduces_available_quantity() -> None:
    result = RiskEngine().evaluate(request(current_notional=Decimal("95000")))
    assert result.allowed is True
    assert result.quantity == Decimal("50")


def test_invalid_config_rejected() -> None:
    with pytest.raises(ValueError, match="risk_per_trade"):
        RiskConfig(risk_per_trade=Decimal("0"))
