# Paper Trading Engine

## Purpose

G6-002 provides a deterministic, broker-free execution simulator for validating the complete decision-to-portfolio path before any broker adapter is enabled.

## Boundary

```text
Strategy Signal
      ↓
Decision Engine
      ↓
Risk Engine
      ↓
Paper Trading Engine
      ↓
Orders → Fills → Positions → PnL
```

The simulator never calls a broker and cannot enable live trading.

## V1 behavior

- market orders only
- LONG/SHORT position direction
- immediate simulated fill at supplied market price
- adverse slippage by basis points
- execution fee by basis points
- deterministic client-order-id deduplication
- chronological event enforcement
- netted positions with average entry price
- realized PnL on position reduction/reversal
- mark-to-market unrealized PnL
- account equity calculation
- immutable domain records

## Explicit limitations

V1 does not yet model exchange-specific order books, partial fills, latency, contract multipliers, lot-size rules, margin, options Greeks, market impact, trading sessions, or broker reconciliation. Those belong in later execution/broker hardening.

## Safety rule

Paper trading is the required validation stage before broker integration. Live execution remains disabled by default and must pass the production acceptance gate.
