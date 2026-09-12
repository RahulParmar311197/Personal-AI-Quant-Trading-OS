# Functional Requirements

## Research
FR-001 The system shall ingest and validate historical market data.
FR-002 The system shall provide multi-timeframe market representations.
FR-003 The system shall calculate deterministic technical, price-action, market-structure, SMC and ICT features.
FR-004 The system shall support options-chain and context-derived features where data is available.
FR-005 The system shall detect documented market regimes.

## Strategy and decision
FR-006 Strategies shall implement a common interface and produce signals/evidence, not broker orders.
FR-007 The decision layer shall combine validated strategy/model evidence and support NO_TRADE.
FR-008 AI/ML inference shall be optional and bounded by explicit contracts.

## Risk and execution
FR-009 The risk engine shall independently approve/reject proposed trades.
FR-010 The system shall support deterministic position sizing, exposure, daily loss and kill-switch controls.
FR-011 The system shall provide paper trading before any live execution path.
FR-012 Broker adapters shall use a common interface and reconcile orders/positions.

## Observability/UI
FR-013 The system shall maintain an auditable signal, decision, risk and order trail.
FR-014 The UI shall consume domain APIs and shall not bypass risk controls.
