# System Architecture

## Logical flow

Market Data
→ Data Validation/Normalization
→ Feature Engineering
→ Market Regime
→ Strategy Engine
→ Opportunity Ranking
→ Decision Engine
→ Risk Engine
→ Execution Engine
→ Broker

Cross-cutting:
- Portfolio state
- Trade journal
- Audit trail
- Monitoring
- Configuration

## Major boundaries

### Data
Owns ingestion, normalization and canonical market data.

### Features
Owns deterministic calculations and feature contracts.

### Strategy
Produces candidate opportunities, not orders.

### Decision
Aggregates strategy/model evidence and returns LONG/SHORT/NO_TRADE.

### Risk
Can approve or reject a decision and determines allowed size/risk parameters.

### Execution
Owns order lifecycle and reconciliation.

### AI/ML
Produces bounded model outputs with versioned artifacts and evaluation.

## Initial deployment
Prefer a modular monolith with clear package boundaries. Split into services only when scaling or isolation requirements justify it.
