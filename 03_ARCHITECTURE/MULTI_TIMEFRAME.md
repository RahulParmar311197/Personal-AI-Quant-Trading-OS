# Multi-Timeframe Aggregation Contract

## Purpose

Provide deterministic higher-timeframe OHLCV bars from canonical lower-timeframe bars. Historical and live consumers use the same aggregation semantics.

## Supported timeframes

`1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`, `1w`.

## Rules

1. Input timestamps must be timezone-aware and are normalized to UTC.
2. Buckets are fixed-duration, UTC epoch-aligned intervals.
3. Open is the first input bar's open.
4. High is the maximum input high.
5. Low is the minimum input low.
6. Close is the last input bar's close.
7. Volume is the sum of input volumes.
8. Provisional input bars are excluded by default.
9. Missing bars are not synthesized or interpolated.
10. No future input bar may influence an earlier bucket.
11. Input ordering is normalized before aggregation.
12. Provider identity is not used to change aggregation mathematics.
13. Session-aware market calendars are a later refinement; they must not silently alter the fixed-duration contract.

## Completeness

An aggregate is `is_final=true` only when every contributing input bar is finalized. A partial bucket remains provisional and must not be treated as a completed signal candle by downstream strategy logic.

## Gap semantics

A gap remains a gap. Consumers may detect it explicitly, but the aggregator does not manufacture candles.
