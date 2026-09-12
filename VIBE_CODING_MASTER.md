# Vibe Coding Master Framework — Personal AI Quant Trading OS

## Mission
Build a personal quantitative trading operating system that converts market data and market-theory signals into researchable, testable and, only after validation, executable decisions.

## Engineering loop
READ → INSPECT → PLAN → IMPLEMENT → TEST → DEBUG → SECURITY REVIEW → REGRESSION TEST → DOCUMENT → UPDATE STATE → COMMIT → NEXT TASK

## Completion levels
L0 IDEA
L1 REQUIREMENTS
L2 ARCHITECTURE
L3 FOUNDATION
L4 DATA
L5 ANALYTICS
L6 STRATEGIES
L7 BACKTEST
L8 AI/ML
L9 DECISION/RISK
L10 PAPER TRADING
L11 BROKER/EXECUTION
L12 STAGING
L13 PRODUCTION

## Trading-specific invariants
- Historical research must be point-in-time correct.
- No look-ahead leakage.
- Every signal must be timestamped.
- Deterministic risk controls must be independent of model output.
- Backtests must model realistic fees/slippage where applicable.
- Live trading is disabled by default.
- Strategy, decision, risk and execution are separate concerns.
- Every live order must be auditable and reconciled.

## Definition of Done
A feature is complete only when requirements, implementation, tests, validation, documentation and applicable security/deployment checks pass.

## Default technology direction
Backend: Python + FastAPI + Pydantic
Data: PostgreSQL/TimescaleDB, Redis, optional ClickHouse
Processing: Polars/Pandas/NumPy/PyArrow
ML: scikit-learn, XGBoost, LightGBM, PyTorch
Frontend: Next.js/React/TypeScript
Charts: TradingView Lightweight Charts
Infrastructure: Docker; CI/CD via GitHub Actions
Observability: Prometheus/Grafana where appropriate

This document is a control framework, not permission to introduce every technology listed above immediately. Prefer the simplest architecture that satisfies current requirements.
