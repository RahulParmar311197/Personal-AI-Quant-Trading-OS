# Non-Functional Requirements

NFR-001 Correctness: calculations and state transitions are deterministic where inputs and configuration are deterministic.
NFR-002 Reproducibility: research runs record data, feature, strategy and configuration versions.
NFR-003 Point-in-time integrity: historical analysis cannot use information unavailable at the event timestamp.
NFR-004 Auditability: signals, decisions, risk results and orders are traceable.
NFR-005 Security: secrets remain outside source control and privileged actions are protected.
NFR-006 Testability: domain logic is unit-testable and critical flows have integration/regression coverage.
NFR-007 Resilience: external data/broker failures fail safely with bounded retries and explicit stale-state handling.
NFR-008 Observability: health, errors, latency and critical trading state are measurable.
NFR-009 Maintainability: domain boundaries are explicit and dependencies flow toward stable contracts.
NFR-010 Performance: V1 must support interactive research/dashboard workloads without requiring premature distributed infrastructure.
