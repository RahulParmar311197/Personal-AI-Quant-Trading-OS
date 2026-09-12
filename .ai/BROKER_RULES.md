# Broker Rules

1. Broker integrations implement the common broker interface.
2. Credentials must come from secure runtime configuration and never source control.
3. Authentication failures fail closed.
4. Broker state is never assumed; order and position state must be reconciled.
5. Duplicate-order protection is mandatory.
6. Timeouts, retries and partial failures must be explicit and bounded.
7. Live execution remains disabled by default.
8. A broker adapter cannot bypass the Risk Engine.
9. Paper-trading behavior must be validated before live adapter enablement.
10. Every live order must have an auditable intent, authorization and lifecycle.
