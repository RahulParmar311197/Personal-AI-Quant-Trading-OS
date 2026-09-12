# Production Checklist

## Data
- [ ] Sources validated
- [ ] Historical quality checks pass
- [ ] Live freshness monitoring exists

## Research
- [ ] Backtest engine validated
- [ ] No-look-ahead checks pass
- [ ] Walk-forward reviewed
- [ ] Robustness/Monte Carlo reviewed

## Risk
- [ ] Risk gateway enforced
- [ ] Kill switch tested
- [ ] Daily limits tested
- [ ] Exposure limits tested

## Execution
- [ ] Paper trading validated
- [ ] Broker adapter tested
- [ ] Reconciliation tested
- [ ] Failure modes tested

## Security
- [ ] No secrets in repository
- [ ] Authentication/authorization reviewed
- [ ] Audit trail enabled

## Operations
- [ ] Monitoring
- [ ] Alerts
- [ ] Backups
- [ ] Restore procedure
- [ ] Rollback plan

## Go-live
- [ ] Live trading explicitly enabled
- [ ] Capital/exposure limits documented
- [ ] Emergency stop verified
