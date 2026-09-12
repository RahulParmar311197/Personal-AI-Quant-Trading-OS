# Strategy Engine — G5-001

## Purpose

The strategy layer converts point-in-time market context into deterministic or
model-backed **research signals**. It does not create broker orders and does
not grant permission to trade.

## Boundary

```text
Market Data / Features / Regime Context
                |
                v
           Strategy Engine
                |
                v
       StrategySignal / evidence
                |
                v
          Decision Engine
                |
                v
            Risk Engine
                |
                v
           Order Intent
                |
                v
        Execution / Broker
```

The invariant is:

> Strategy output is evidence, not execution authority.

A strategy must never call a broker, submit an order, mutate portfolio state,
or bypass the risk engine.

## Contracts

### `StrategyMetadata`

Provides stable `name`, `version`, description, and tags for experiment and
trade provenance. Multiple versions of one strategy name may coexist, but an
unversioned lookup becomes invalid when more than one version is registered.

### `StrategyContext`

Contains:

- an explicit UTC-aware `as_of` timestamp;
- a chronological tuple of historical bars ending at or before `as_of`;
- a point-in-time feature snapshot.

Future bars are rejected at construction. Feature mappings are copied and
exposed read-only, preventing accidental mutation of the supplied snapshot.

### `StrategySignal`

Contains:

- observation timestamp;
- `LONG`, `SHORT`, or `FLAT` side;
- confidence in `[0, 1]` using `Decimal`;
- human/audit-readable evidence;
- optional suggested stop/target levels.

It deliberately contains no quantity, broker, account, order type, or
execution instruction. Position sizing and trade permission belong downstream.

### `Strategy`

Implementations expose immutable metadata and implement:

```python
evaluate(context: StrategyContext) -> StrategySignal | None
```

The method is expected to be side-effect free.

### `StrategyRegistry`

The V1 registry is process-local and explicit. It supports:

- registration at application startup;
- lookup by `name + version`;
- lookup by name only when exactly one version exists;
- metadata enumeration;
- duplicate identity rejection;
- unknown-strategy rejection.

Persistence, remote discovery, hot reload, and strategy marketplace concerns
are intentionally outside G5-001.

## No-look-ahead policy

A strategy receives only the information available at its observation time.
For a bar-close strategy this means:

```text
bar T closes
   |
   +--> build context through T
   |
   +--> strategy evaluates at T
   |
   +--> decision/risk may act on the signal
   |
   +--> execution model determines the earliest legal fill
```

Strategies must not query future bars or future feature values. Backtests must
preserve the same temporal contract as live evaluation.

## Future strategy families

The registry is intentionally strategy-family agnostic. Future implementations
can consume the existing technical, market-structure, SMC, and ICT feature
contracts, plus regime, volume, options, macro/news/sentiment and ML outputs.
Those implementations should be added only after their own deterministic
feature and validation contracts exist.

## V1 non-goals

- automatic strategy discovery;
- strategy-generated broker orders;
- portfolio/risk permission inside strategies;
- claims of predictive accuracy;
- live-trading enablement;
- optimization of strategy parameters inside the registry.
