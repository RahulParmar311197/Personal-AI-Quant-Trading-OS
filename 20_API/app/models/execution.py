"""Durable execution records and idempotency identity."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ExecutionOrder(Base):
    __tablename__ = "execution_orders"

    client_order_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False)
    instrument_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("instruments.instrument_id", ondelete="RESTRICT"), nullable=False
    )
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False)
    requested_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    filled_quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="CREATED")
    signal_event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_message: Mapped[str] = mapped_column(Text, nullable=False, default="")

    __table_args__ = (
        UniqueConstraint("strategy_id", "signal_event_time", "instrument_id", "side", name="uq_execution_signal_identity"),
        CheckConstraint("side IN ('BUY', 'SELL')", name="ck_execution_side"),
        CheckConstraint("order_type IN ('MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT')", name="ck_execution_order_type"),
        CheckConstraint("requested_quantity > 0", name="ck_execution_requested_qty"),
        CheckConstraint("filled_quantity >= 0 AND filled_quantity <= requested_quantity", name="ck_execution_filled_qty"),
        CheckConstraint("status IN ('CREATED','SUBMITTED','ACKNOWLEDGED','PARTIALLY_FILLED','FILLED','CANCEL_PENDING','CANCELLED','REJECTED','UNKNOWN','RECONCILED','FAILED')", name="ck_execution_status"),
        Index("ix_execution_orders_status", "status"),
        Index("ix_execution_orders_instrument", "instrument_id"),
    )
