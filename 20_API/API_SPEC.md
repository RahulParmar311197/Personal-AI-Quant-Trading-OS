# API Baseline

The API exposes versioned contracts for health, instruments, candles, market state, analysis, strategies, backtests, paper trading, portfolio, orders, journal and risk.

Rules:
- APIs validate inputs and outputs.
- Authentication/authorization are explicit for protected operations.
- No endpoint may bypass domain-level risk controls.
- Order endpoints must return auditable identifiers and lifecycle state.
- External adapter details stay behind stable domain contracts.
