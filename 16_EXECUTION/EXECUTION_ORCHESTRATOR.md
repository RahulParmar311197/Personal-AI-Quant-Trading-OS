# Execution Orchestrator

## Responsibility

The execution layer is the only component allowed to translate a risk-approved quantity into a broker order request.

```text
Strategy Signal
      ↓
Decision
      ↓
Risk Authorization
      ↓
ExecutionIntent
      ↓
Durable Order Identity
      ↓
ExecutionOrderRepository
      ↓
ExecutionEngine
      ↓
BrokerAdapter
      ↓
Reconciliation
```

## V1 safety properties

- denied risk decisions never reach a broker
- live execution is disabled by default
- broker health is checked before submission
- client order IDs are durable database identities when a repository is supplied
- duplicate IDs are idempotent only for the exact same intent; conflicting reuse is rejected
- requested quantity cannot exceed risk authorization
- broker-specific types remain behind the adapter contract
- execution does not calculate strategy signals or risk sizing
- the database transaction is owned by the application workflow; the repository flushes but does not commit

## Durable lifecycle

Orders use the normalized lifecycle:

`CREATED → SUBMITTED → ACKNOWLEDGED → PARTIALLY_FILLED → FILLED → RECONCILED`

Cancellation and failure paths are explicit. An ambiguous broker response transitions to `UNKNOWN` and **must not be automatically retried**. Reconciliation must establish the broker's actual state first.

## Failure semantics

```text
Broker call
   │
   ├── confirmed result → persist normalized state
   │
   └── exception/timeout → UNKNOWN
                              ↓
                        reconcile broker
                              ↓
                    only then decide next action
```

## Persistence boundary

`ExecutionOrderRepository` provides:

- transactional reservation of `client_order_id`
- durable strategy/signal/instrument identity
- broker order ID persistence
- lifecycle transition validation through `OrderStateMachine`
- monotonic fill-quantity protection
- active-order lookup for reconciliation

The repository is provider-neutral. Upstox, future brokers, paper execution, and other adapters do not own persistence semantics.

## V1 limitations

- durable repository integration requires a database-backed application transaction
- broker position/order snapshots still need a production reconciliation scheduler
- partial-fill event ingestion remains adapter/provider dependent
- durable event-sourced audit history is still pending
- automatic retry policy is intentionally not implemented
- live execution remains disabled until sandbox and production acceptance gates are completed
