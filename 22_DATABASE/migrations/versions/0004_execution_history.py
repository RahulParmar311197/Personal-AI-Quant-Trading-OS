"""Persist execution lifecycle audit events and broker fills.

Revision ID: 0004_execution_history
Revises: 0003_execution_orders
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_execution_history"
down_revision = "0003_execution_orders"
branch_labels = None
depends_on = None


_EXECUTION_STATUSES = "'CREATED','SUBMITTED','ACKNOWLEDGED','PARTIALLY_FILLED','FILLED','CANCEL_PENDING','CANCELLED','REJECTED','UNKNOWN','RECONCILED','FAILED'"


def upgrade() -> None:
    op.create_table(
        "execution_audit_events",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("client_order_id", sa.String(length=128), nullable=False),
        sa.Column("broker_order_id", sa.String(length=128), nullable=True),
        sa.Column("from_status", sa.String(length=24), nullable=True),
        sa.Column("to_status", sa.String(length=24), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.CheckConstraint(f"to_status IN ({_EXECUTION_STATUSES})", name="ck_execution_audit_to_status"),
        sa.ForeignKeyConstraint(["client_order_id"], ["execution_orders.client_order_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_execution_audit_order_time", "execution_audit_events", ["client_order_id", "event_time"], unique=False)

    op.create_table(
        "execution_fills",
        sa.Column("broker_fill_id", sa.String(length=128), nullable=False),
        sa.Column("client_order_id", sa.String(length=128), nullable=False),
        sa.Column("broker_order_id", sa.String(length=128), nullable=True),
        sa.Column("instrument_id", sa.String(length=128), nullable=False),
        sa.Column("side", sa.String(length=4), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("fill_price", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("fee", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.CheckConstraint("side IN ('BUY', 'SELL')", name="ck_execution_fill_side"),
        sa.CheckConstraint("quantity > 0", name="ck_execution_fill_quantity"),
        sa.CheckConstraint("fill_price > 0", name="ck_execution_fill_price"),
        sa.CheckConstraint("fee >= 0", name="ck_execution_fill_fee"),
        sa.ForeignKeyConstraint(["client_order_id"], ["execution_orders.client_order_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("broker_fill_id"),
    )
    op.create_index("ix_execution_fills_order_time", "execution_fills", ["client_order_id", "event_time"], unique=False)
    op.create_index("ix_execution_fills_broker_order", "execution_fills", ["broker_order_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_execution_fills_broker_order", table_name="execution_fills")
    op.drop_index("ix_execution_fills_order_time", table_name="execution_fills")
    op.drop_table("execution_fills")
    op.drop_index("ix_execution_audit_order_time", table_name="execution_audit_events")
    op.drop_table("execution_audit_events")
