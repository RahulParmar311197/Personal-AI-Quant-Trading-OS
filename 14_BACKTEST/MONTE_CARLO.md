# Monte Carlo Backtest Robustness

## Purpose

Monte Carlo analysis tests how sensitive a strategy's realized trade outcomes are to sequencing and sampling. The V1 implementation bootstraps realized net trade P&Ls with replacement and recomputes the resulting equity path.

## Reported measures

- median final capital
- 5th percentile final capital
- 95th percentile final capital
- median absolute maximum drawdown
- 95th percentile absolute maximum drawdown
- probability of finishing below initial capital
- probability of reaching zero or below

## Reproducibility

Every simulation uses an explicit seed. The same input trades, configuration and seed must produce the same summary.

## Important interpretation

This is a robustness analysis of realized outcomes, not a model of future market prices. It does not create new price paths, account for changing market regimes, or establish statistical significance. It must be combined with out-of-sample and walk-forward validation.

## Safety boundary

Monte Carlo results are research evidence only. They cannot authorize live execution and cannot bypass the independent risk engine.
