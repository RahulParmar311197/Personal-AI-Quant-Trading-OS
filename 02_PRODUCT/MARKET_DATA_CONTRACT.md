# Canonical Market Data Contract

## Scope

This contract defines the normalized market-data envelope used by downstream features, strategies, backtests, paper trading and execution. It does not define broker-specific payloads.

## Design principles

1. Preserve source provenance and event time.
2. Normalize timestamps to UTC internally.
3. Never silently overwrite source data.
4. Validate numerical relationships before publishing an event.
5. Keep instrument identity separate from provider-specific symbols.
6. Historical and live data must use the same canonical representation.
7. Every downstream consumer must be able to determine whether data is complete, delayed or stale.

## Canonical instrument identity

Required fields:

- `instrument_id`: stable internal identifier.
- `exchange`: exchange code, e.g. `NSE`.
- `segment`: cash, index, futures, options, etc.
- `symbol`: normalized symbol.
- `provider_symbol`: source-specific symbol when applicable.
- `currency`: ISO currency code.
- `timezone`: exchange/session timezone.
- `expiry`: nullable contract expiry.
- `strike`: nullable option strike.
- `option_type`: nullable `CE`/`PE`.

## Canonical OHLCV bar

Required:

- `event_time`: UTC bar timestamp.
- `ingested_at`: UTC ingestion timestamp.
- `instrument_id`.
- `timeframe`.
- `open`, `high`, `low`, `close`.
- `volume`.
- `source`.
- `sequence`: source sequence when available.
- `is_final`: whether the bar is closed/final.

Validation:

- `high >= max(open, close, low)`.
- `low <= min(open, close, high)`.
- Prices must be finite and non-negative where the instrument contract requires it.
- Volume must be finite and non-negative.
- Duplicate `(instrument_id, timeframe, event_time, source)` records must be detected.

## Tick / quote envelope

Required when available:

- `event_time`.
- `ingested_at`.
- `instrument_id`.
- `last_price`.
- `last_quantity`.
- `bid_price`, `bid_quantity`.
- `ask_price`, `ask_quantity`.
- `cumulative_volume`.
- `source`.

A crossed quote (`bid_price > ask_price`) is invalid unless explicitly permitted by the source adapter and flagged.

## Order-book snapshot

Required when supplied by a source:

- `event_time`.
- `ingested_at`.
- `instrument_id`.
- ordered bid levels.
- ordered ask levels.
- `depth`.
- `source`.

Each level contains price and quantity. Source sequence identifiers should be retained where provided.

## Options snapshot

Required where applicable:

- instrument identity including expiry, strike and option type.
- underlying instrument identifier.
- event and ingestion timestamps.
- LTP / bid / ask where available.
- volume.
- open interest.
- open-interest change when supplied by source.
- implied volatility when supplied or derived under a documented model.
- Greeks only when the calculation model, inputs and timestamp are recorded.

## Data-quality state

Every published market-data record may carry a quality state:

- `VALID` — passed required validation.
- `DEGRADED` — usable with known quality limitations.
- `STALE` — outside the consumer's freshness threshold.
- `INVALID` — failed validation and must not feed trading decisions.

## Point-in-time rule

Historical reconstruction must use only information that was available at or before the record's effective event time. Revised vendor data must retain revision/provenance information rather than silently creating look-ahead information.

## Storage boundary

G2 database implementation will map this contract to normalized relational tables and time-series indexes. Domain-specific schemas for features, strategies, orders and portfolio state belong to later gates and must not be mixed into the market-data canonical schema.
