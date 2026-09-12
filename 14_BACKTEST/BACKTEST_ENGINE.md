# Event-Driven Backtest Engine

## Purpose

The V1 backtest engine provides a deterministic research execution loop. It is intentionally separate from broker execution and live trading.

## Point-in-time model

A strategy receives the current bar and historical prefix ending at that bar. A signal created from bar close cannot execute at that same close. The engine queues it and executes at the **next bar open**.

```text
bar T closes
   ↓
signal(T)
   ↓
pending order
   ↓
bar T+1 opens
   ↓
fill(T+1)
```

This is the primary V1 look-ahead control.

## V1 execution model

- single position at a time
- LONG/SHORT signals
- quantity explicitly supplied by strategy
- next-bar-open execution
- deterministic adverse slippage
- configurable half-spread
- configurable basis-point fees
- gross and net P&L
- immutable fills/trades/results

The cost model applies slippage plus half the configured spread against the trader's execution price. Fees are calculated from executed notional.

## Data integrity

Bars must have timezone-aware, strictly increasing timestamps. Future-dated signals are rejected. The engine does not manufacture missing bars.

## Deliberately deferred

The following remain separate tasks:

- stop-loss/target simulation
- intrabar execution policy
- partial fills
- market impact
- order queueing
- portfolio-level margin
- options Greeks/margin
- walk-forward validation
- Monte Carlo analysis
- parameter optimization

## Safety boundary

Backtesting does not enable live trading. Broker credentials and real-money execution are outside this module.
