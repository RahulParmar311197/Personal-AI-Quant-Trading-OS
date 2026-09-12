"""Persist provider-neutral execution order identity and lifecycle state.

Revision ID: 0003_execution_orders
Revises: 0002_market_data_foundation
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_execution_orders"
down_revision = "0002_market_data_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "execution_orders",
        sa.Column("client_order_id", sa.String(length=128), nullable=False),
        sa.Column("broker_order_id", sa.String(length=128), nullable=True),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("instrument_id", sa.String(length=128), nullable=False),
        sa.Column("side", sa.String(length=4), nullable=False),
        sa.Column("order_type", sa.String(length=16), nullable=False),
        sa.Column("requested_quantity", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("filled_quantity", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("signal_event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_message", sa.Text(), nullable=False),
        sa.CheckConstraint("side IN ('BUY', 'SELL')", name="ck_execution_side"),
        sa.CheckConstraint("order_type IN ('MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT')", name="ck_execution_order_type"),
        sa.CheckConstraint("requested_quantity > 0", name="ck_execution_requested_qty"),
        sa.CheckConstraint("filled_quantity >= 0 AND filled_quantity <= requested_quantity", name="ck_execution_filled_qty"),
        sa.CheckConstraint("status IN ('CREATED','SUBMITTED','ACKNOWLEDGED','PARTIALLY_FILLED','FILLED','CANCEL_PENDING','CANCELLED','REJECTED','UNKNOWN','RECONCILED','FAILED')", name="ck_execution_status"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.instrument_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("client_order_id"),
        sa.UniqueConstraint("broker_order_id", name="uq_execution_broker_order_id"),
        sa.UniqueConstraint("strategy_id", "signal_event_time", "instrument_id", "side", name="uq_execution_signal_identity"),
    )
    op.create_index("ix_execution_orders_status", "execution_orders", ["status"], unique=False)
    op.create_index("ix_execution_orders_instrument", "execution_orders", ["instrument_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_execution_orders_instrument", table_name="execution_orders")
    op.drop_index("ix_execution_orders_status", table_name="execution_orders")
    op.drop_table("execution_orders")
