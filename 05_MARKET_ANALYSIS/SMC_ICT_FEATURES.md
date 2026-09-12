# Deterministic SMC / ICT Feature Contract

This layer converts commonly used SMC/ICT concepts into explicit research definitions. Terminology in discretionary trading communities varies, so every implementation rule is versioned by this project rather than treated as universal truth.

## Implemented

### Liquidity
- Confirmed swing highs form candidate buy-side liquidity.
- Confirmed swing lows form candidate sell-side liquidity.
- Consecutive same-kind swings within a configurable relative tolerance form an equal-liquidity pool.

### Fair Value Gap
For three candles A/B/C:
- bullish FVG when `C.low > A.high`
- bearish FVG when `C.high < A.low`

The gap boundaries are the non-overlapping wick prices. The event is emitted only when candle C exists.

### Displacement / Order Block
A displacement candle must have range greater than the trailing average range multiplied by a configurable factor. The immediately preceding opposite-direction candle is recorded as the corresponding order block.

This is a project-specific deterministic research definition and is not asserted to be the only or canonical ICT/SMC definition.

### Premium / Discount
For a trailing range:
- equilibrium = `(range_high + range_low) / 2`
- close above equilibrium → PREMIUM
- close below equilibrium → DISCOUNT
- equal → EQUILIBRIUM

## No-look-ahead

Every feature is calculated only from bars that exist at the feature event time. No future candle is consulted to define a historical FVG, liquidity pool, displacement or premium/discount classification.

## Deliberately deferred

- liquidity sweeps
- inducement
- mitigation blocks
- breaker blocks
- session-specific dealing ranges
- previous-day/week high/low
- Asian/London/New York session models
- OTE
- ICT kill zones

These require additional explicit session/calendar contracts before implementation.

## Safety boundary

SMC/ICT features are evidence. They are not trade permission and cannot bypass strategy validation or the independent Risk Engine.
