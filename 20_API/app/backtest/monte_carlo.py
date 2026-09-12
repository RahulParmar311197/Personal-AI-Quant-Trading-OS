"""Monte Carlo robustness analysis for backtest trade outcomes."""

from dataclasses import dataclass
from decimal import Decimal
import random
from typing import Sequence

from app.backtest.engine import Trade


@dataclass(frozen=True)
class MonteCarloConfig:
    simulations: int = 1_000
    seed: int = 42
    initial_capital: Decimal = Decimal("100000")

    def __post_init__(self) -> None:
        if self.simulations <= 0:
            raise ValueError("simulations must be positive")
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")


@dataclass(frozen=True)
class MonteCarloSummary:
    simulations: int
    original_trade_count: int
    median_final_capital: Decimal
    p05_final_capital: Decimal
    p95_final_capital: Decimal
    median_max_drawdown: Decimal
    p95_max_drawdown: Decimal
    probability_of_loss: Decimal
    probability_of_ruin: Decimal


def max_drawdown(equity: Sequence[Decimal]) -> Decimal:
    """Return absolute peak-to-trough drawdown for an equity curve."""
    if not equity:
        return Decimal("0")
    peak = equity[0]
    worst = Decimal("0")
    for value in equity:
        if value > peak:
            peak = value
        drawdown = peak - value
        if drawdown > worst:
            worst = drawdown
    return worst


def _percentile(values: Sequence[Decimal], fraction: Decimal) -> Decimal:
    if not values:
        raise ValueError("values cannot be empty")
    ordered = sorted(values)
    position = (Decimal(len(ordered) - 1) * fraction)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - Decimal(lower)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def run_monte_carlo(
    trades: Sequence[Trade],
    config: MonteCarloConfig | None = None,
) -> MonteCarloSummary:
    """Bootstrap trade P&Ls with replacement and report robustness percentiles.

    This deliberately analyzes realized trade outcomes rather than generating
    synthetic prices. It tests path dependence and outcome variability; it is
    not a substitute for out-of-sample validation or a stochastic market model.
    """
    cfg = config or MonteCarloConfig()
    outcomes = [trade.net_pnl for trade in trades]
    if not outcomes:
        return MonteCarloSummary(
            simulations=0,
            original_trade_count=0,
            median_final_capital=cfg.initial_capital,
            p05_final_capital=cfg.initial_capital,
            p95_final_capital=cfg.initial_capital,
            median_max_drawdown=Decimal("0"),
            p95_max_drawdown=Decimal("0"),
            probability_of_loss=Decimal("0"),
            probability_of_ruin=Decimal("0"),
        )

    rng = random.Random(cfg.seed)
    finals: list[Decimal] = []
    drawdowns: list[Decimal] = []
    losses = 0
    ruins = 0
    ruin_threshold = Decimal("0")

    for _ in range(cfg.simulations):
        equity = cfg.initial_capital
        curve = [equity]
        for _trade in range(len(outcomes)):
            equity += rng.choice(outcomes)
            curve.append(equity)
        finals.append(equity)
        drawdowns.append(max_drawdown(curve))
        if equity < cfg.initial_capital:
            losses += 1
        if min(curve) <= ruin_threshold:
            ruins += 1

    simulations = cfg.simulations
    return MonteCarloSummary(
        simulations=simulations,
        original_trade_count=len(outcomes),
        median_final_capital=_percentile(finals, Decimal("0.50")),
        p05_final_capital=_percentile(finals, Decimal("0.05")),
        p95_final_capital=_percentile(finals, Decimal("0.95")),
        median_max_drawdown=_percentile(drawdowns, Decimal("0.50")),
        p95_max_drawdown=_percentile(drawdowns, Decimal("0.95")),
        probability_of_loss=Decimal(losses) / Decimal(simulations),
        probability_of_ruin=Decimal(ruins) / Decimal(simulations),
    )
