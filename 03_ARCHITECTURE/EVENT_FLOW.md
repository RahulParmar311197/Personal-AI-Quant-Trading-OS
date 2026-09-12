# Event Flow

Core domain events should be immutable facts with explicit event timestamps and identifiers.

```text
MarketDataReceived
  -> MarketDataValidated
  -> FeaturesUpdated
  -> RegimeUpdated
  -> StrategySignalCreated
  -> DecisionCreated
  -> RiskEvaluated
  -> OrderIntentAuthorized
  -> OrderSubmitted
  -> OrderUpdated/Filled/Rejected
  -> PositionUpdated
  -> JournalRecorded
```

Not every event occurs in every workflow. Paper trading substitutes a simulator for the broker while preserving the order lifecycle contract. Event consumers must be idempotent where duplicate delivery is possible.
