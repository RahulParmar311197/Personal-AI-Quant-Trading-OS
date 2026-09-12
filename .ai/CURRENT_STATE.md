# Current State

Date: 2026-09-12

## Repository state
G5 strategy-layer foundation is now progressing on `framework/bootstrap`.

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
- G5-001 strategy registry/base contracts: metadata, point-in-time context, non-executable strategy signals, versioned registry and tests.

## In progress
- G1-001 Python backend foundation; runtime test execution is still required.
- G1-002 frontend foundation; runtime install/build/test validation is still required.
- G1-003 database migration foundation; runtime Alembic/database validation is still required.
- G1-004 Docker development environment; build/runtime validation is still required.
- G2/G3/G4 implementation tasks are present and tested by committed unit/contract suites; runtime validation remains pending.
- G5-001 strategy registry/base interface; runtime validation remains pending.

## Pending
- G5-002 regime engine.
- G5-003 decision engine.
- G5-004 independent risk engine.
- G6 ML, paper trading, broker contracts/adapters.
- G7 dashboard, observability, production acceptance and controlled rollout.

## Known technical debt / follow-up
- `BacktestEngine` still owns its original fee/slippage arithmetic instead of consuming the new `CostModel`; integrate before declaring G4 production-ready.
- Runtime CI/local validation is still required.
- Exchange-session-aware daily/weekly aggregation remains a future market-calendar enhancement.

## Blocked
- Runtime validation cannot be performed through the connected GitHub repository interface; local execution or CI is required for runtime-dependent acceptance.

## Critical safety status
Live trading is disabled.
