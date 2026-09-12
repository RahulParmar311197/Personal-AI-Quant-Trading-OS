# Current State

Date: 2026-09-12

## Repository state
Execution/broker hardening is progressing on `framework/bootstrap` with live trading still disabled.

## Completed implementation work
- G0-001 project control files and agent rules.
- G0-002 V1 requirements, functional/non-functional requirements, user stories, acceptance criteria and traceability.
- G0-003 target architecture, component boundaries, data flow, event flow and security architecture.
- Initial FastAPI backend foundation under `20_API/`.
- Database foundation: SQLAlchemy session/base, environment-driven `DATABASE_URL`, Alembic configuration/environment and initial migration baseline.
- Frontend foundation: Next.js/React shell, strict TypeScript configuration, safety-first home page, responsive base styling and Vitest smoke-test setup.
- Docker development stack: PostgreSQL, Redis, backend/frontend services and health-gated dependencies.
- G2 canonical market-data contract and validation rules documented.
- Executable G2 market-data persistence foundation: canonical `Instrument` and OHLCV `Bar` SQLAlchemy models, Alembic migration, constraints/indexes and contract tests.
- G2-002 historical ingestion contract: bounded requests, canonical normalized bars, provider port, pagination/cursor protection and ingestion tests.
- G2-003 live adapter contract: canonical event envelope, provider port, deduplication, sequence protection, stale detection and tests.
- G3-001 multi-timeframe aggregation: deterministic UTC bucket alignment, OHLCV aggregation, provisional-bar handling and tests.
- G3-002 technical feature engine: point-in-time technical indicators and tests.
- G3-003 market-structure engine: confirmed swings, HH/HL/LH/LL, BOS/CHOCH and tests.
- G3-004 deterministic SMC/ICT feature contracts: liquidity pools, FVG, displacement/order-block and premium/discount features plus tests.
- G4-001 deterministic backtest engine with next-bar-open execution and no-look-ahead controls.
- G4-002 execution cost model for fees, slippage and spread.
- G4-003 chronological walk-forward validation contracts and tests.
- G4-004 bootstrap Monte Carlo outcome robustness analysis and tests.
- G5 strategy/regime/decision/risk foundations.
- G6 ML training/evaluation contracts, paper-trading simulator, provider-neutral broker contract and first Upstox adapter.
- Execution hardening V1: normalized order lifecycle state machine, durable SQL execution-order schema/migration, idempotency contract, fail-closed order/position reconciliation service and orchestration.
- Upstox reconciliation discovery: adapter now implements current-day order-book listing through `/v2/order/retrieve-all`, enabling broker-only order discovery rather than only targeted local-order lookups.
- Execution reservation hardening: duplicate inserts are isolated with a SQLAlchemy SAVEPOINT so an idempotency race does not roll back the caller's outer transaction.
- G6-004-H3 reconciliation runner/snapshot cadence contract and tests.
- Database model import-cycle regression fix and explicit regression test.

## In progress
- CI runtime validation is being rerun after fixing the SQLAlchemy model import cycle.
- PostgreSQL-specific transactional repository validation is pending the clean CI run.
- Upstox sandbox end-to-end acceptance remains pending; no user credentials are stored or used by this repository workflow.
- Durable execution audit/fill history remains pending.

## Pending
- G6-004-H2 PostgreSQL transactional validation.
- G6-004-H4 Upstox sandbox acceptance.
- G6-004-H5 durable execution audit history and fill ingestion.
- G7 dashboard, observability/audit trail, production acceptance and controlled rollout.

## Known technical debt / follow-up
- `BacktestEngine` still owns its original fee/slippage arithmetic instead of consuming the new `CostModel`; integrate before declaring G4 production-ready.
- Some earlier tests have weak typing/assertions and should be tightened during runtime validation.
- Exchange-session-aware daily/weekly aggregation remains a future market-calendar enhancement.
- Upstox order placement deliberately disables broker auto-slicing in V1 to preserve one internal order identity per broker result.
- Upstox's order book is current-day only; cross-session historical reconciliation requires separate durable local history and/or provider history endpoints.

## Blocked
- Runtime validation cannot be performed through the connected GitHub repository interface; local execution or CI is required for runtime-dependent acceptance.
- Upstox sandbox acceptance requires an explicitly supplied sandbox credential; no credential is available to this workflow.

## Critical safety status
Live trading is disabled.
