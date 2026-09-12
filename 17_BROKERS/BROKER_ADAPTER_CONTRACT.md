# Broker Adapter Contract

## Purpose

G6-003 defines the normalized boundary between the trading platform and an external broker. Concrete broker APIs must implement this contract rather than leaking provider-specific request/response models into the core system.

## Architecture

```text
Decision
   ↓
Risk Authorization
   ↓
Execution Orchestrator
   ↓
BrokerAdapter
   ↓
Concrete Provider Adapter
   ↓
External Broker
```

The broker adapter is an execution integration. It does not generate strategy signals and does not replace the independent risk engine.

## Required operations

- `place_order`
- `cancel_order`
- `get_order`
- `get_account`
- `get_positions`
- `healthcheck`

## Normalized contracts

Orders support MARKET, LIMIT, STOP, and STOP_LIMIT types. Requests carry an application-generated `client_order_id` for idempotency/reconciliation.

Results normalize broker order identity, client identity, status, filled quantity, average fill price, and a provider message.

Fills normalize broker fill identity, order identity, instrument, side, quantity, price, event timestamp, and fees.

Capabilities explicitly declare what a provider supports. Unsupported order types must be rejected before sending an external request.

## Safety requirements for concrete adapters

1. Never bypass RiskEngine.
2. Never enable live trading merely because an adapter is configured.
3. Never commit API credentials.
4. Preserve broker IDs and timestamps for reconciliation.
5. Treat network timeout as unknown execution state until reconciled; never blindly retry an order that may have been accepted.
6. Enforce client-order-id idempotency.
7. Normalize provider status into the platform status model.
8. Surface broker health failures to the execution/observability layer.
9. Reconcile orders and positions after uncertain responses.
10. Keep paper and live adapters behind the same normalized boundary.

## Deliberate non-goals

G6-003 does not connect to Upstox, Zerodha, Binance, or another live broker. A first concrete adapter is G6-004 and is gated on paper-trading validation and production acceptance controls.
