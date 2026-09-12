# Architecture Rules

Use this dependency direction:

Data → Features → Regime → Strategy → Decision → Risk → Execution

Supporting systems:
- Portfolio/Journaling consume execution events.
- Backtesting reuses strategy/risk/execution abstractions through simulation.
- AI/ML consumes governed features and produces bounded outputs.
- UI calls APIs; it must not own trading business logic.

Do not allow:
- UI directly placing broker orders
- Strategy directly bypassing Risk
- AI directly bypassing Risk
- Backtest code reading future bars
