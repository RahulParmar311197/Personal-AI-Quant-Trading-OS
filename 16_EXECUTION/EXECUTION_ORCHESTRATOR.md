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
ExecutionEngine
      ↓
BrokerAdapter
```

## V1 safety properties

- denied risk decisions never reach a broker
- live execution is disabled by default
- broker health is checked before submission
- client order IDs are required and deduplicated within the process
- requested quantity cannot exceed risk authorization
- broker-specific types remain behind the adapter contract
- execution does not calculate strategy signals or risk sizing

## Failure semantics

A broker timeout or ambiguous response must not be treated as an automatic failure in a future production adapter. The adapter/execution state machine must reconcile the client order ID with broker state before any retry.

## V1 limitations

The current orchestration layer is intentionally small. Durable idempotency, persistent order state, reconciliation, partial-fill handling, retries, kill-switch integration, and event-sourced audit records are production-hardening work.
