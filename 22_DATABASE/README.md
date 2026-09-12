# Database Foundation

This directory owns database migrations and database-specific architecture.

## Stack

- PostgreSQL as the primary relational database.
- SQLAlchemy 2.x for application persistence.
- Alembic for schema migrations.
- `psycopg` as the PostgreSQL driver.

## Boundaries

- Domain tables are **not** created during G1. They belong to later gates after their contracts are defined.
- Application code obtains its database URL from `DATABASE_URL` through `20_API/app/core/config.py`.
- Migration execution must use the same environment-driven URL as the application.
- Secrets and credentials must never be committed to the repository.

## Local commands

From the repository root:

```bash
alembic -c 22_DATABASE/alembic.ini current
alembic -c 22_DATABASE/alembic.ini upgrade head
alembic -c 22_DATABASE/alembic.ini downgrade base
```

The default local URL is intended only for development. Set `DATABASE_URL` in the environment for any real deployment.
