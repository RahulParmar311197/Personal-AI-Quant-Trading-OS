# Trading Rules

1. Research code must be point-in-time correct.
2. A signal is not an order.
3. Strategy output is not permission to trade.
4. Risk engine can reject any strategy decision.
5. Live trading is opt-in and disabled by default.
6. Every order must have a traceable decision and risk evaluation.
7. Execution must reconcile broker state against local state.
8. Backtests must model the limitations of available market data.
9. Do not claim profitability from backtests alone.
10. Avoid optimizing solely for win rate; evaluate expectancy, drawdown and robustness.
