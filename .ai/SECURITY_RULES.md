# Security Rules

- Never store broker/API credentials in Git.
- Use environment variables or a secret manager.
- Never log credentials, tokens or sensitive account data.
- Validate all external inputs.
- Apply least privilege.
- Protect administrative and order endpoints.
- Audit security-sensitive actions.
- Treat broker callbacks/webhooks as untrusted inputs.
