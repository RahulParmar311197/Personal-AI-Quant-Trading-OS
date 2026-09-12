"""Canonical model registration for SQLAlchemy metadata."""

# Import every mapped model exactly once so ``Base.metadata`` contains the
# complete application schema for runtime tooling and migration discovery.
from app.models.execution import ExecutionOrder  # noqa: F401
from app.models.execution_history import ExecutionAuditEvent, ExecutionFill  # noqa: F401
from app.models.market_data import Bar, Instrument  # noqa: F401

__all__ = ["Bar", "Instrument", "ExecutionOrder", "ExecutionAuditEvent", "ExecutionFill"]
