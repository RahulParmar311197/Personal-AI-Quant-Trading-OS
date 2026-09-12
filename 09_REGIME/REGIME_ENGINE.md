# Market Regime Engine

## Purpose

The regime engine classifies the current market context before strategy selection. It is descriptive context, not a trade signal, order authority, or risk approval mechanism.

## V1 regimes

- `TREND_UP` — directional positive return with price at/above EMA.
- `TREND_DOWN` — directional negative return with price at/below EMA.
- `RANGE` — neither directional threshold is satisfied.
- `HIGH_VOLATILITY` — current candle range exceeds the configured volatility threshold; this takes precedence over ordinary trend labels.
- `UNKNOWN` — required warm-up inputs are unavailable.

## Point-in-time guarantee

Classification consumes one `TechnicalFeatures` snapshot at a time. `classify_series()` requires strictly increasing timestamps and does not inspect future rows when classifying the current row.

## Confidence and auditability

Every result contains component scores for trend, volatility, and volume plus human-readable reasons. Scores are bounded to `[0, 1]`.

The V1 technical feature contract exposes volume SMA but not a current-volume ratio. Consequently the volume score remains neutral until a dedicated point-in-time volume-ratio feature is introduced. The engine does not infer missing information.

## Boundaries

```text
Market Data → Features → Regime → Strategy Selection → Decision → Risk → Execution
```

The regime engine must not:

- place or modify orders;
- call broker APIs;
- approve risk;
- consume future bars;
- claim predictive certainty;
- silently substitute missing features.

## Future extensions

Session-aware regime models, ADX/trend-strength, volatility estimators, realized volatility, volume-ratio features, multi-timeframe regime fusion, and ML regime classification can be added behind explicit versioned contracts.
