# Technical Feature Engine

The technical engine provides deterministic, point-in-time features for downstream market analysis. It does not generate orders or override the independent risk boundary.

## Current feature set

### Trend
- SMA
- EMA

### Momentum
- RSI
- MACD and signal line
- percentage returns

### Volatility
- ATR
- Bollinger middle/upper/lower bands

### Volume
- volume SMA

### Candle structure
- range percentage
- body percentage
- upper-wick percentage
- lower-wick percentage

## Point-in-time contract

For output row `t`, every calculation uses only bars with event time at or before `t`. Future rows cannot change an already-produced feature row. Warm-up periods return `None`; they are never backfilled with future observations.

## Data requirements

Input bars must have timezone-aware timestamps and strictly increasing event times after sorting. OHLCV validity is inherited from the canonical market-data contract.

## Numerical policy

Decimal arithmetic is used for price-domain calculations where practical. Standard deviation is converted from a floating square-root operation back to Decimal; this is sufficient for the current deterministic research contract and should be replaced with a fully Decimal implementation if numerical audit requirements demand it.

## Boundary

The feature engine is evidence generation only. Strategy logic may consume features, but the feature engine cannot place, modify, approve, or bypass an order.
