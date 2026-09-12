# Risk Rules

Risk is independent from strategy and AI.

Minimum controls for live enablement:
- Per-trade risk cap
- Daily loss cap
- Max open positions
- Max portfolio exposure
- Leverage/exposure limits
- Slippage/spread guard
- Duplicate-order guard
- Stale-data guard
- Broker connectivity guard
- Kill switch
- Reconciliation check

Any failed critical risk control must produce NO TRADE / CANCEL / EXIT behavior according to the policy.
