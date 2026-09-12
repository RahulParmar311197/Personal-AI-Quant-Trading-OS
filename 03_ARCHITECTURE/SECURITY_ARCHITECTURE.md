# Security Architecture

## Trust boundaries
- External market/news/broker systems are untrusted inputs.
- API is an authenticated transport boundary.
- Domain services validate all external data and commands.
- Broker credentials are runtime secrets only.

## Controls
- Least-privilege credentials.
- No secrets in Git.
- Input/schema validation at boundaries.
- Explicit authorization for privileged actions.
- Audit trail for risk and order state transitions.
- Fail-closed behavior for authentication, stale data and risk-control failures.
- Live execution disabled by default.
