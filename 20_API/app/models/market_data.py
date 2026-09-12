"""Canonical market-data persistence models for the database foundation."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Instrument(Base):
    """Stable internal identity for a tradable or reference market instrument."""

    __tablename__ = "instruments"

    instrument_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    segment: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_symbol: Mapped[str | None] = mapped_column(String(128))
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    asset_type: Mapped[str] = mapped_column(String(16), nullable=False)
    expiry: Mapped[date | None] = mapped_column(Date)
    strike: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    option_type: Mapped[str | None] = mapped_column(String(2))

    bars: Mapped[list["Bar"]] = relationship(back_populates="instrument")

    __table_args__ = (
        UniqueConstraint(
            "exchange",
            "segment",
            "symbol",
            "expiry",
            "strike",
            "option_type",
            name="uq_instruments_contract_identity",
        ),
        CheckConstraint(
            "asset_type IN ('EQUITY', 'INDEX', 'FUTURE', 'OPTION', 'OTHER')",
            name="ck_instruments_asset_type",
        ),
        CheckConstraint(
            "option_type IS NULL OR option_type IN ('CE', 'PE')",
            name="ck_instruments_option_type",
        ),
        CheckConstraint(
            "asset_type = 'OPTION' OR (expiry IS NULL AND strike IS NULL AND option_type IS NULL)",
            name="ck_instruments_option_fields",
        ),
        Index("ix_instruments_exchange_symbol", "exchange", "symbol"),
    )


class Bar(Base):
    """Canonical OHLCV bar persisted with source and point-in-time metadata."""

    __tablename__ = "bars"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instrument_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("instruments.instrument_id", ondelete="RESTRICT"), nullable=False
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    event_time: Mapped[datetime] = mapped_column(nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    sequence: Mapped[int | None] = mapped_column(BigInteger)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    quality: Mapped[str] = mapped_column(String(16), nullable=False, default="VALID")

    instrument: Mapped[Instrument] = relationship(back_populates="bars")

    __table_args__ = (
        UniqueConstraint(
            "instrument_id", "timeframe", "event_time", "source", name="uq_bars_point_in_time"
        ),
        CheckConstraint("high >= low", name="ck_bars_high_gte_low"),
        CheckConstraint("high >= open AND high >= close", name="ck_bars_high_gte_prices"),
        CheckConstraint("low <= open AND low <= close", name="ck_bars_low_lte_prices"),
        CheckConstraint("volume >= 0", name="ck_bars_non_negative_volume"),
        CheckConstraint("quality IN ('VALID', 'DEGRADED', 'STALE', 'INVALID')", name="ck_bars_quality"),
        Index("ix_bars_instrument_timeframe_event", "instrument_id", "timeframe", "event_time"),
        Index("ix_bars_event_time", "event_time"),
    )
