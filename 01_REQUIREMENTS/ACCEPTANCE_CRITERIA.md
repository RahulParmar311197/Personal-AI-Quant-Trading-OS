# V1 Acceptance Criteria

## A. Foundation
- Repository follows the frozen framework.
- Governance/state files exist and are internally consistent.
- Application can be started through documented development commands once G1 is implemented.

## B. Data and research
- Canonical market-data contracts validate required fields and timestamps.
- Historical processing rejects or flags invalid OHLC data, duplicates and unacceptable gaps according to documented policy.
- Feature calculations demonstrate no future-data dependency through deterministic leakage tests.

## C. Analysis
- Multi-timeframe aggregation has deterministic timestamp semantics and boundary tests.
- Technical, price-action, structure, SMC and ICT concepts have documented definitions and unit tests for representative cases.

## D. Backtest and validation
- Backtest execution is event-driven and does not read future bars/features.
- Fees/slippage and configured execution assumptions are represented.
- Walk-forward and Monte Carlo results are reproducible from recorded configurations.

## E. Decision and risk
- Decision engine can return NO_TRADE.
- Risk engine can reject strategy/AI proposals independently.
- Position sizing and hard exposure/loss limits are deterministic and tested.

## F. Paper/live execution
- Paper trading can simulate order lifecycle and reconciliation.
- Live trading remains disabled by default.
- Live execution cannot be enabled until paper validation, risk controls, reconciliation, kill switch, security and production acceptance gates pass.

## G. Operations/security
- Secrets are externalized.
- Critical events are auditable.
- Health/error/latency signals are observable.
- Regression tests cover critical trading paths.
