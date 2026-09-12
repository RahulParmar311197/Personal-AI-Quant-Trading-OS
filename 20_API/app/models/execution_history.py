"""Durable execution lifecycle audit and broker-fill records."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ExecutionAuditEvent(Base):
    __tablename__ = "execution_audit_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_order_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("execution_orders.client_order_id", ondelete="CASCADE"), nullable=False
    )
    broker_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    from_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    to_status: Mapped[str] = mapped_column(String(24), nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")

    __table_args__ = (
        CheckConstraint("to_status IN ('CREATED','SUBMITTED','ACKNOWLEDGED','PARTIALLY_FILLED','FILLED','CANCEL_PENDING','CANCELLED','REJECTED','UNKNOWN','RECONCILED','FAILED')", name="ck_execution_audit_to_status"),
        Index("ix_execution_audit_order_time", "client_order_id", "event_time"),
    )


class ExecutionFill(Base):
    __tablename__ = "execution_fills"

    broker_fill_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    client_order_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("execution_orders.client_order_id", ondelete="CASCADE"), nullable=False
    )
    broker_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    instrument_id: Mapped[str] = mapped_column(String(128), nullable=False)
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    fill_price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False, default=0)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        CheckConstraint("side IN ('BUY', 'SELL')", name="ck_execution_fill_side"),
        CheckConstraint("quantity > 0", name="ck_execution_fill_quantity"),
        CheckConstraint("fill_price > 0", name="ck_execution_fill_price"),
        CheckConstraint("fee >= 0", name="ck_execution_fill_fee"),
        Index("ix_execution_fills_order_time", "client_order_id", "event_time"),
        Index("ix_execution_fills_broker_order", "broker_order_id"),
    )
