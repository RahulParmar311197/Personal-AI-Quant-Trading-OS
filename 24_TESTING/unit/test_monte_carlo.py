from decimal import Decimal

import pytest

from app.backtest.engine import Fill, Trade
from app.backtest.monte_carlo import MonteCarloConfig, max_drawdown, run_monte_carlo


def trade(pnl: str) -> Trade:
    entry = Fill(None, "LONG", Decimal("1"), Decimal("100"), Decimal("0"))
    exit_fill = Fill(None, "LONG", Decimal("1"), Decimal("100"), Decimal("0"))
    return Trade(entry, exit_fill, Decimal(pnl), Decimal(pnl))


def test_max_drawdown() -> None:
    assert max_drawdown([Decimal("100"), Decimal("120"), Decimal("90"), Decimal("110")]) == Decimal("30")


def test_monte_carlo_is_deterministic_with_seed() -> None:
    trades = [trade("10"), trade("-5"), trade("20"), trade("-8")]
    config = MonteCarloConfig(simulations=100, seed=7, initial_capital=Decimal("100"))
    assert run_monte_carlo(trades, config) == run_monte_carlo(trades, config)


def test_monte_carlo_loss_probability_for_all_winners_is_zero() -> None:
    result = run_monte_carlo([trade("10"), trade("5")], MonteCarloConfig(simulations=50))
    assert result.probability_of_loss == Decimal("0")
    assert result.probability_of_ruin == Decimal("0")


def test_invalid_simulation_count_is_rejected() -> None:
    with pytest.raises(ValueError):
        MonteCarloConfig(simulations=0)
