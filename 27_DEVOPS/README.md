# Development Environment

This directory contains the reproducible local development stack.

## Services

- PostgreSQL 17 — relational persistence.
- Redis 8 — cache/event infrastructure baseline.
- FastAPI backend — port `8000`.
- Next.js frontend — port `3000`.

## Start

```bash
docker compose -f 27_DEVOPS/docker-compose.dev.yml up --build
```

The development stack deliberately keeps `LIVE_TRADING_ENABLED=false`.

## Database migrations

The backend image contains the Alembic configuration. From the repository root:

```bash
docker compose -f 27_DEVOPS/docker-compose.dev.yml exec backend alembic -c 22_DATABASE/alembic.ini current
docker compose -f 27_DEVOPS/docker-compose.dev.yml exec backend alembic -c 22_DATABASE/alembic.ini upgrade head
```

## Production boundary

This compose file is development-only. It does not provide production secrets, broker credentials, live execution, HA guarantees, or production data retention policy.
