# Independent Risk Engine

## Purpose

The risk engine is the hard authorization boundary between a trading decision and an executable order intent.

```text
Decision Engine
      ↓
RiskRequest
      ↓
RISK ENGINE
 ├─ kill switch
 ├─ live/paper permission
 ├─ daily loss limit
 ├─ open-position limit
 ├─ stop-distance validation
 ├─ risk-per-trade sizing
 └─ notional cap
      ↓
RiskDecision
      ↓
Order Intent / Execution
```

## V1 position sizing

For a stop-based position:

`risk_amount = account_equity × risk_per_trade`

`quantity_by_risk = risk_amount / abs(entry_price - stop_price)`

The permitted quantity is additionally capped by the configured notional limit, existing notional, and any requested quantity.

## Safety invariants

1. Kill switch always denies.
2. Daily loss limit always denies when breached.
3. Maximum open positions cannot be bypassed by strategy or AI.
4. Stop distance must be within configured bounds.
5. Quantity is computed independently of strategy confidence.
6. Risk returns an authorization decision, not a broker order.
7. Live trading remains disabled by default; a disabled-live request can still be evaluated for paper/research authorization.

V1 deliberately does not model margin, options Greeks, portfolio correlation, liquidity impact, or exchange-specific lot sizes. Those belong to later risk/execution extensions and must be added without weakening this boundary.
