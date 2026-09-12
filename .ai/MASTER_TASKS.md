# Master Tasks

| ID | Priority | Task | Status |
|---|---|---|---|
| G0-001 | P0 | Establish project control files and agent rules | DONE |
| G0-002 | P0 | Freeze V1 requirements and acceptance criteria | DONE |
| G0-003 | P0 | Define target architecture and boundaries | DONE |
| G1-001 | P0 | Create Python backend foundation | IN_PROGRESS |
| G1-002 | P0 | Create frontend foundation | IN_PROGRESS |
| G1-003 | P0 | Create database migration foundation | IN_PROGRESS |
| G1-004 | P1 | Add Docker development environment | IN_PROGRESS |
| G2-001 | P0 | Define market-data canonical schema and executable persistence mapping | IN_PROGRESS |
| G2-002 | P0 | Implement historical data ingestion contract | IN_PROGRESS |
| G2-003 | P0 | Implement live data adapter interface | IN_PROGRESS |
| G3-001 | P0 | Implement multi-timeframe aggregation | IN_PROGRESS |
| G3-002 | P0 | Implement technical feature engine | IN_PROGRESS |
| G3-003 | P0 | Implement market-structure engine | IN_PROGRESS |
| G3-004 | P0 | Implement deterministic SMC/ICT feature contracts | IN_PROGRESS |
| G4-001 | P0 | Build backtest engine with no-look-ahead controls | IN_PROGRESS |
| G4-002 | P0 | Add realistic execution/cost model | DONE |
| G4-003 | P1 | Add walk-forward validation | IN_PROGRESS |
| G4-004 | P1 | Add Monte Carlo analysis | IN_PROGRESS |
| G5-001 | P0 | Create strategy registry and base interface | IN_PROGRESS |
| G5-002 | P0 | Create regime engine | IN_PROGRESS |
| G5-003 | P0 | Create decision engine with explicit high-volatility fail-closed guard | DONE |
| G5-004 | P0 | Create independent risk engine | IN_PROGRESS |
| G6-001 | P1 | Add ML training/evaluation pipeline | IN_PROGRESS |
| G6-002 | P0 | Create paper-trading simulator | IN_PROGRESS |
| G6-003 | P0 | Create broker adapter contract | IN_PROGRESS |
| G6-004 | P0 | Implement first broker adapter only after paper validation | IN_PROGRESS |
| G6-004-H1 | P0 | Harden execution with durable order lifecycle, idempotency and fail-closed reconciliation | DONE |
| G6-004-H2 | P0 | Validate transactional execution repository against PostgreSQL | DONE |
| G6-004-H3 | P0 | Add broker order/position snapshot reconciliation scheduler | DONE |
| G6-004-H4 | P0 | Complete Upstox sandbox acceptance | IN_PROGRESS |
| G6-004-H5 | P1 | Add durable execution audit history and fill ingestion | DONE |
| G7-001 | P1 | Create trading dashboard | IN_PROGRESS |
| G7-002 | P1 | Add observability and audit trail | BACKLOG |
| G7-003 | P0 | Production acceptance and controlled rollout | BACKLOG |

## Branch policy

- `main` is the sole development and integration branch.
- All future implementation commits must be made directly on `main`.
- `framework/bootstrap` is no longer an active development branch.
- Do not create or use feature branches for this project unless the user explicitly changes this policy.

## Current implementation sequence
1. CI validation is the authoritative gate for recent execution and backtest/decision hardening changes.
2. Upstox sandbox acceptance remains opt-in and credential-gated.
3. Continue remaining execution hardening that is not credential-gated, then address the next highest-priority incomplete canonical task.
4. G7-001 dashboard work starts as a read-only, safety-first operator surface; it must not create an execution bypass.
5. Keep live trading disabled until controlled production acceptance criteria are satisfied.
