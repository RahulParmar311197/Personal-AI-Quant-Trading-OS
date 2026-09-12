# Data Rules

- Store timestamps in UTC internally; convert only at presentation boundaries.
- Preserve source timestamps and ingestion timestamps.
- Keep symbol/instrument identity versioned.
- Validate duplicates, gaps and impossible OHLC relationships.
- Corporate actions and contract-roll assumptions must be explicit.
- Historical datasets must not contain information unavailable at the decision timestamp.
- Every derived feature must declare its lookback and timestamp semantics.
