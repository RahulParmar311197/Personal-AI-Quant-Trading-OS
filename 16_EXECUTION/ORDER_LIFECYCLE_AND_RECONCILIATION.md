# Order Lifecycle and Reconciliation

## Purpose

Execution is treated as a durable state machine rather than a single broker API call. The local system owns the normalized lifecycle; broker-specific states are translated at the adapter boundary.

## Lifecycle

```text
CREATED
  -> SUBMITTED
  -> ACKNOWLEDGED
  -> PARTIALLY_FILLED -> FILLED
  -> CANCEL_PENDING -> CANCELLED
  -> RECONCILED
```

Failure/uncertainty paths are explicit:

- `REJECTED`: broker definitively rejected the order.
- `FAILED`: local processing failed before a broker state can be trusted.
- `UNKNOWN`: the broker response is ambiguous, including timeout/network failure. **Never automatically retry an order in UNKNOWN.** Reconcile first.
- `RECONCILED`: terminal state has been compared with authoritative broker state.

## Durable identity

`client_order_id` is the primary local identity. The database also enforces a unique `(strategy_id, signal_event_time, instrument_id, side)` identity so a repeated signal cannot silently create a second order intent.

The current in-memory idempotency store is only a deterministic test/local-development implementation. Production orchestration must reserve the identity transactionally in `execution_orders` before calling a broker.

## Reconciliation

Reconciliation is read-only and fail-closed. It compares:

1. local durable orders vs broker order snapshots;
2. local filled quantity vs broker filled quantity;
3. local positions vs broker positions.

Any mismatch produces a finding and `healthy=False`. Reconciliation does not submit, retry, or cancel orders as a side effect.

## Safety rules

- No automatic retry after an ambiguous broker response.
- No live execution by default.
- Do not mark an order `FILLED` solely because a placement request returned successfully; broker status/fill data must support it.
- Do not declare execution healthy while open-order or position reconciliation has unresolved discrepancies.
- Provider instrument identifiers remain adapter-specific and must be mapped from the canonical internal instrument identity before execution.

## V1 limitations

- Persistence model is defined, but repository/transaction wiring into `ExecutionEngine` is still pending.
- Broker order listing/streaming is not yet part of the provider-neutral adapter contract, so reconciliation currently accepts snapshots supplied by an integration layer.
- Partial-fill event persistence, execution audit events, retries after proven-safe transient failures, and exchange-specific session/lot rules remain future hardening work.
