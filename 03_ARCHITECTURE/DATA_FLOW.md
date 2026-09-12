# Data Flow

```text
External Sources
  -> Ingestion Adapters
  -> Raw/Source Metadata
  -> Validation & Normalization
  -> Canonical Market Data
  -> Timeframe Aggregation
  -> Feature Engine
  -> Regime Engine
  -> Strategy / AI Evidence
  -> Decision Engine
  -> Risk Engine
  -> Execution Simulator or Broker
  -> Portfolio / Journal / Audit
```

Historical and live paths share canonical contracts but have different execution policies. Historical research must preserve event-time semantics and prohibit future-data access. Live paths must reject stale or invalid data before order authorization.
