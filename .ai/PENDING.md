# Pending Work

The authoritative task list is `.ai/MASTER_TASKS.md`.

## Current priority
- Runtime validation of G1-G6 implementation through local execution or CI.
- G4-002: integrate the execution `CostModel` into `BacktestEngine` before G4 production acceptance.
- G5 decision/risk hardening: explicitly deny directional entries in `HIGH_VOLATILITY` unless a dedicated strategy/risk policy authorizes them.
- G6-004-H2: validate transactional execution repository integration against PostgreSQL.
- G6-004-H3: implement broker order/position snapshot reconciliation scheduler.
- G6-004-H4: execute Upstox sandbox acceptance with a real sandbox credential supplied at runtime; never commit credentials.
- G6-004-H5: add durable event/audit history and broker fill ingestion.
- G7-001: trading dashboard.
- G7-002: observability and audit trail.
- G7-003: production acceptance and controlled rollout.

## Validation note
Repository changes can be inspected and committed through the connected GitHub interface, but local Python/Alembic execution is not available in this session. Do not mark runtime-dependent gates fully DONE until the documented local or CI validation commands succeed.

## Safety gate
Live trading remains disabled. Sandbox validation must pass before any production broker authorization is considered.
