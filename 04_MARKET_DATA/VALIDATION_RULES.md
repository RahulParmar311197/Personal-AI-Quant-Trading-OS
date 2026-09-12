# Market Data Validation Rules

## Hard failures

Reject a record as `INVALID` when:

- required identity or event timestamp is absent;
- timestamp cannot be parsed unambiguously;
- OHLC values violate high/low relationships;
- required numeric values are NaN or infinite;
- volume/quantity is negative where the contract prohibits it;
- an impossible contract identity is supplied;
- a duplicate event violates the source uniqueness contract and is not an allowed correction.

## Degraded records

Use `DEGRADED` when a source legitimately omits optional fields or publishes a partial update, provided the downstream consumer's contract can safely tolerate the omission.

## Stale records

`STALE` is determined by consumer-specific freshness thresholds. A stale record must not silently be treated as current data by signal generation or execution components.

## Revisions

Vendor corrections must be represented as corrections/revisions with provenance. Historical data must not be overwritten in a way that destroys the ability to reproduce the original point-in-time dataset.

## Gap handling

Missing bars are not automatically backfilled by interpolation. Gap detection is explicit; any repair/backfill operation records its source and method and is unavailable to live execution unless explicitly permitted by the data contract.

## Look-ahead protection

Any field whose effective timestamp is later than the decision timestamp is prohibited from the decision dataset. Feature and strategy layers inherit this point-in-time requirement.
