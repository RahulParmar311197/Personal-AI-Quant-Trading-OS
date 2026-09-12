# Upstox Sandbox Acceptance

## Purpose

Validate the real Upstox adapter against the Upstox sandbox before any live
broker rollout. This gate is deliberately opt-in and does not authorize live
trading.

Upstox documents the sandbox as a risk-free environment for end-to-end API
integration testing. The current documentation marks Place Order V3 and
Cancel Order V3 as sandbox-enabled. The adapter therefore uses a LIMIT order
for the acceptance flow and immediately attempts cancellation.

## Required environment

Set these only in the local shell or CI secret environment. Never commit them:

```text
UPSTOX_SANDBOX_ACCESS_TOKEN=<sandbox token>
UPSTOX_SANDBOX_INSTRUMENT_TOKEN=<sandbox instrument token>
UPSTOX_SANDBOX_LIMIT_PRICE=<positive limit price>
```

Optional:

```text
UPSTOX_SANDBOX_BASE_URL=https://sandbox.upstox.com
```

The test skips when any required variable is absent. A sandbox credential is
not required for normal unit/database CI.

## Run locally

From the repository root:

```bash
set UPSTOX_SANDBOX_ACCESS_TOKEN=...
set UPSTOX_SANDBOX_INSTRUMENT_TOKEN=...
set UPSTOX_SANDBOX_LIMIT_PRICE=...
python -m pytest 24_TESTING/integration/test_upstox_sandbox.py -q
```

PowerShell:

```powershell
$env:UPSTOX_SANDBOX_ACCESS_TOKEN="..."
$env:UPSTOX_SANDBOX_INSTRUMENT_TOKEN="..."
$env:UPSTOX_SANDBOX_LIMIT_PRICE="..."
python -m pytest 24_TESTING/integration/test_upstox_sandbox.py -q
```

## Acceptance sequence

1. Verify HTTPS sandbox configuration.
2. Authenticate through the adapter healthcheck.
3. Place one BUY LIMIT order for quantity 1.
4. Read the order back from Upstox.
5. Request cancellation.
6. Read the order again and accept the broker's terminal outcome. A fill can
   legitimately race the cancellation in a sandbox, so the harness accepts
   `CANCELLED`, `FILLED`, or `PARTIALLY_FILLED`.
7. Retrieve the current order book and verify that the test order is
   discoverable.

The test intentionally does not place a MARKET order. Choose the instrument
and limit price so the sandbox order is suitable for a cancellation test.

## CI policy

Normal CI runs the test file with no sandbox credential and therefore records a
skip. A real sandbox run must be explicitly configured with the three required
secrets and must be treated as a separate acceptance run. No workflow should
fall back from sandbox credentials to live credentials.

## Evidence required before H4 is marked DONE

- The acceptance test completes successfully using an actual Upstox sandbox
  token.
- The observed broker order ID is captured in the CI/job evidence, not stored
  in source code.
- Place, inspect, cancel, final inspection, and order-book discovery all pass.
- No live base URL or live credential is used.
- Live trading remains disabled in the platform.

## Upstox references

See the official Upstox sandbox and order API documentation for current
sandbox capabilities and endpoint behavior.
