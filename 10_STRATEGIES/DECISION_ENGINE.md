# Decision Engine

## Purpose

The decision engine converts research evidence into an auditable **decision proposal**. It is not an order router and it is not the risk authority.

## Boundary

```text
StrategySignal + MarketRegime + optional AI probability
                         ↓
                  Decision Engine
                         ↓
             LONG / SHORT / NO_TRADE
                         ↓
                    Risk Engine
                         ↓
                    Order Intent
```

## V1 scoring

Default weights:

- Strategy confidence: 60%
- Regime alignment: 20%
- AI directional probability: 20%

The aggregate score must meet the configured minimum threshold. Strategy confidence must also meet its minimum threshold.

## Safety rules

1. `UNKNOWN` regime produces `NO_TRADE`.
2. Missing strategy signal produces `NO_TRADE`.
3. `FLAT` strategy output produces `NO_TRADE`.
4. A future-dated strategy signal is rejected.
5. AI probability is evidence only; it cannot bypass strategy or risk.
6. The decision engine does not calculate quantity, margin, stop permission, or broker orders.
7. Every decision carries reasons and component scores for auditability.

## Directional alignment

- LONG aligns fully with `TREND_UP`.
- SHORT aligns fully with `TREND_DOWN`.
- `RANGE` receives neutral alignment in V1.
- Opposing trend and high-volatility/unknown contexts do not receive directional approval.

This is a deterministic V1 contract, not a claim of predictive accuracy. Thresholds must be validated using out-of-sample research before deployment.
