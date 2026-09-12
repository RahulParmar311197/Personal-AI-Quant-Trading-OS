# Market Structure Engine

## Deterministic definitions

The market-structure layer converts canonical OHLCV into confirmed swing points and structure events. It is an analysis layer only.

### Swing high
A candle is a swing high when its high is strictly greater than every high in the configured left and right confirmation windows.

### Swing low
A candle is a swing low when its low is strictly lower than every low in the configured left and right confirmation windows.

Ties are rejected. A swing cannot be confirmed until the required right-side bars exist. This is the explicit confirmation delay and prevents hindsight labeling.

### Structure labels
For consecutive confirmed swings of the same kind:

- High above prior high → HH
- High below prior high → LH
- Low above prior low → HL
- Low below prior low → LL

### BOS / CHOCH
A break requires a candle close strictly beyond the most recent eligible confirmed swing level.

- BOS: break continues the established directional state.
- CHOCH: break changes the established directional state.

The first directional break is treated as BOS because there is no prior direction to reverse.

## No-look-ahead rule

A structure event at time `T` may only reference swing points whose confirmation time is before `T`. A future candle can create a newly confirmed swing, but it cannot retroactively become an input to an already emitted break event.

## Limitations

This is the initial deterministic market-structure contract. Equal highs/lows, liquidity pools, inducement, protected highs/lows, displacement and session-specific structure are intentionally deferred to the SMC/ICT layer where their definitions can be versioned explicitly.
