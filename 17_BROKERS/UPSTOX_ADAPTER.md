# Upstox Adapter

## Selection

Upstox is the first concrete broker adapter because its current developer platform provides a sandbox environment and sandbox-enabled order V3 APIs. The adapter is therefore implemented sandbox-first.

Current official integration facts used by this adapter:

- Upstox documents Place Order V3 as sandbox-enabled.
- Place Order V3 returns one or more broker order IDs and supports automatic slicing.
- Cancel Order V3 is sandbox-enabled.
- Upstox recommends V3 replacements for several older V2 order APIs.
- OAuth 2.0 is the authentication mechanism; secrets/tokens are not stored in this repository.

## Configuration

```text
UPSTOX_ACCESS_TOKEN=<sandbox token>
```

The application must inject the token at runtime. Never commit it.

The adapter defaults to:

```text
https://sandbox.upstox.com
```

The base URL is injectable for controlled environment configuration.

## Instrument identity

`BrokerOrderRequest.instrument_id` is interpreted by this adapter as the **Upstox provider instrument token**, for example `NSE_EQ|...` or `NSE_FO|...`. Internal instrument identity must be resolved to a provider token before reaching the adapter.

## V1 supported mapping

| Internal | Upstox |
|---|---|
| BUY/SELL | transaction_type |
| MARKET | MARKET |
| LIMIT | LIMIT |
| STOP | SL-M |
| STOP_LIMIT | SL |
| quantity | integer quantity |
| limit_price | price |
| stop_price | trigger_price |
| client_order_id | tag |

Auto-slicing is deliberately disabled in V1 so one internal order remains one broker-order result. Multi-order/sliced execution requires an explicit fan-out contract later.

## Safety

This adapter does not itself enable live trading. The execution engine remains the final live-execution gate, and its default is `live_enabled=False`.

Sandbox credentials and requests must be tested before any consideration of a live base URL.
