# Durable Execution History

## Purpose

Execution history is the immutable evidence layer beneath the mutable
`execution_orders` snapshot. It prevents the current order row from becoming
the only record of what happened and provides durable inputs for reconciliation,
incident analysis, and later portfolio/trade-journal workflows.

## Tables

### `execution_audit_events`

Records every durable order lifecycle observation written by the repository:

- initial `CREATED` reservation
- broker submission/acknowledgement
- partial/full fills
- cancellation/rejection
- unknown/reconciliation/failure transitions

Each record contains an immutable event ID, client/broker order identity,
previous and next status, event timestamp, recording timestamp, source, and
message.

### `execution_fills`

Records individual provider fills. `broker_fill_id` is the provider identity
and primary idempotency key. A replay of the same fill returns the existing row;
reusing that ID with different economics is rejected.

Stored economics:

- client/broker order IDs
- instrument and side
- fill quantity
- fill price
- fee
- provider event timestamp
- local recording timestamp
- source/provider identity

## Transaction semantics

Order lifecycle state and audit records are written in the caller's transaction.
Fill ingestion writes the fill and then advances the durable order fill quantity
and lifecycle state in the same transaction boundary.

Idempotency races use SQLAlchemy SAVEPOINTs so a duplicate insert cannot poison
the caller's outer transaction.

## Fill lifecycle

For an order with requested quantity `Q` and current filled quantity `F`:

```text
new cumulative = F + fill.quantity

new cumulative < Q  -> PARTIALLY_FILLED
new cumulative = Q  -> FILLED
new cumulative > Q  -> reject
```

The broker fill must match the durable order's instrument and side. If a broker
order ID is present, it must match the order's known broker identity.

## Provider boundary

The current normalized `BrokerOrderResult` does not claim to contain a provider
fill ID. Therefore broker-specific fill discovery must normalize a real provider
fill ID into `FillIngestRequest` before persistence. The repository must never
invent a fill ID from price, quantity, or timestamps.

## Reconciliation integration

The audit/fill history is the durable evidence layer. Reconciliation can compare
broker snapshots to the current order state while fill history preserves the
individual execution facts that produced the state.

Future hardening can add broker-specific fill-history endpoints, event-stream
consumers, and portfolio position ledgers without changing the core fill
idempotency contract.
