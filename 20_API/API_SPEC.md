# API Baseline

The API exposes versioned contracts for health, instruments, candles, market state, analysis, strategies, backtests, paper trading, portfolio, orders, journal and risk.

## Dashboard

`GET /api/v1/dashboard/state` is a read-only operator endpoint. It exposes runtime mode and safety state without credentials, order controls, or broker secrets.

Rules:
- APIs validate inputs and outputs.
- Authentication/authorization are explicit for protected operations.
- No endpoint may bypass domain-level risk controls.
- Order endpoints must return auditable identifiers and lifecycle state.
- External adapter details stay behind stable domain contracts.
- Dashboard state must remain observational; it cannot authorize or submit orders.
