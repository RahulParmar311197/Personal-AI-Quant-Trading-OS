from decimal import Decimal

import pytest

from app.backtest.costs import CostModel


def test_long_execution_price_includes_adverse_costs() -> None:
    model = CostModel(fee_bps=Decimal("3"), slippage_bps=Decimal("2"), spread_bps=Decimal("4"))
    price = model.execution_price(Decimal("100"), "LONG")
    assert price == Decimal("100.04")


def test_short_execution_price_is_adverse() -> None:
    model = CostModel(slippage_bps=Decimal("2"), spread_bps=Decimal("4"))
    price = model.execution_price(Decimal("100"), "SHORT")
    assert price < Decimal("100")


def test_fee_is_bps_of_notional() -> None:
    model = CostModel(fee_bps=Decimal("5"))
    assert model.fee(Decimal("100"), Decimal("10")) == Decimal("0.5")


def test_negative_cost_is_rejected() -> None:
    with pytest.raises(ValueError):
        CostModel(fee_bps=Decimal("-1"))
