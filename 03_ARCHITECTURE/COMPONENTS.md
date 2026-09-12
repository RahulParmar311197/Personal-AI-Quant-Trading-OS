# Components and Boundaries

| Component | Owns | Must not own |
|---|---|---|
| Market Data | source adapters, canonical events, validation | strategy decisions |
| Features | deterministic calculations and feature contracts | broker actions |
| Regime | market-state classification | order authorization |
| Strategy | candidate signals/opportunities | risk approval/order placement |
| AI/ML | model training/inference artifacts | direct execution |
| Decision | evidence aggregation and LONG/SHORT/NO_TRADE | broker calls |
| Risk | limits, sizing, approval/rejection, kill switch | signal generation |
| Execution | order lifecycle, retries, reconciliation | strategy logic |
| Broker | exchange/broker protocol adaptation | portfolio policy |
| Portfolio | positions, P&L, exposure, attribution | signal generation |
| Journal/Audit | immutable trace of decisions/trades/events | execution authorization |
| API | transport/authentication and DTO mapping | domain business logic |
| Frontend | presentation and user interaction | bypassing APIs/risk |
