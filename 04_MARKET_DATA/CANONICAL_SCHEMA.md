# Market Data Canonical Schema

This is the implementation-facing schema baseline for G2. It intentionally separates identity, time, provenance, quality and payload fields.

## Market data event envelope

```text
MarketDataEvent
├── event_id: UUID
├── instrument_id: string
├── exchange: string
├── segment: string
├── symbol: string
├── provider: string
├── provider_event_id: string | null
├── event_time: UTC timestamp
├── ingested_at: UTC timestamp
├── quality: VALID | DEGRADED | STALE | INVALID
├── sequence: integer | null
└── payload: typed market-data payload
```

`event_id` is an internal event identifier and must not be treated as a provider sequence number.

## Instrument

```text
Instrument
├── instrument_id: string (stable internal key)
├── exchange: string
├── segment: string
├── symbol: string
├── provider_symbol: string | null
├── currency: string
├── timezone: string
├── asset_type: EQUITY | INDEX | FUTURE | OPTION | OTHER
├── expiry: date | null
├── strike: decimal | null
└── option_type: CE | PE | null
```

A derivative contract is identified independently of its underlying instrument. Provider mappings belong to ingestion metadata, not to downstream strategy logic.

## OHLCV bar

```text
Bar
├── instrument_id
├── timeframe
├── event_time
├── ingested_at
├── open
├── high
├── low
├── close
├── volume
├── source
├── sequence | null
└── is_final
```

Canonical uniqueness for a source bar is `(instrument_id, timeframe, event_time, source)`.

## Quote/tick

```text
QuoteTick
├── instrument_id
├── event_time
├── ingested_at
├── last_price | null
├── last_quantity | null
├── bid_price | null
├── bid_quantity | null
├── ask_price | null
├── ask_quantity | null
├── cumulative_volume | null
├── source
└── sequence | null
```

## Order book

```text
OrderBookSnapshot
├── instrument_id
├── event_time
├── ingested_at
├── depth
├── bids[] -> {price, quantity}
├── asks[] -> {price, quantity}
├── source
└── sequence | null
```

## Options snapshot

```text
OptionSnapshot
├── instrument_id
├── underlying_instrument_id
├── expiry
├── strike
├── option_type
├── event_time
├── ingested_at
├── ltp | null
├── bid_price | null
├── ask_price | null
├── volume | null
├── open_interest | null
├── oi_change | null
├── implied_volatility | null
├── delta | null
├── gamma | null
├── theta | null
├── vega | null
├── model_name | null
└── source
```

Greeks are data products, not raw facts. If derived, the model, inputs and calculation timestamp must be retained.

## Validation and publication

The ingestion boundary validates source payloads and emits canonical events only after structural validation. Invalid records are retained in a quarantine/error path where practical and never become trading inputs.

Required quality controls include:

- timestamp validity and ordering checks;
- duplicate detection;
- OHLC relationship checks;
- non-negative quantity/volume checks;
- stale-data thresholds;
- source/provenance retention;
- missing-field policy by data type;
- explicit handling of revisions and corrections.

## Time semantics

All persisted timestamps use UTC. Exchange-local session calendars and trading-day semantics are represented explicitly by the market/session layer and are never inferred from server local time.

## Future extensions

Additional feeds such as fundamentals, macro, news and sentiment must not overload this schema. They receive their own canonical contracts under their respective gates and are joined downstream using explicit timestamps and provenance.
