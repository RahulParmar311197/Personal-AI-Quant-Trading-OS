# Testing Rules

Minimum expectations:
- Unit tests for deterministic domain logic
- Integration tests for database/external boundaries
- Contract tests for adapters
- Backtest regression tests for core strategy behavior
- Risk-engine tests including reject scenarios
- Execution lifecycle tests
- API tests
- End-to-end tests for critical user workflows

Never delete or weaken a failing test solely to make CI green.
