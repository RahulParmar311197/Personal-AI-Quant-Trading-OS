"""Create canonical instrument and OHLCV bar tables.

Revision ID: 0002_market_data_foundation
Revises: 0001_initial_baseline
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_market_data_foundation"
down_revision = "0001_initial_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("instrument_id", sa.String(length=128), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("segment", sa.String(length=32), nullable=False),
        sa.Column("symbol", sa.String(length=128), nullable=False),
        sa.Column("provider_symbol", sa.String(length=128), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("asset_type", sa.String(length=16), nullable=False),
        sa.Column("expiry", sa.Date(), nullable=True),
        sa.Column("strike", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("option_type", sa.String(length=2), nullable=True),
        sa.CheckConstraint(
            "asset_type IN ('EQUITY', 'INDEX', 'FUTURE', 'OPTION', 'OTHER')",
            name="ck_instruments_asset_type",
        ),
        sa.CheckConstraint(
            "option_type IS NULL OR option_type IN ('CE', 'PE')",
            name="ck_instruments_option_type",
        ),
        sa.CheckConstraint(
            "asset_type = 'OPTION' OR (expiry IS NULL AND strike IS NULL AND option_type IS NULL)",
            name="ck_instruments_option_fields",
        ),
        sa.PrimaryKeyConstraint("instrument_id"),
        sa.UniqueConstraint(
            "exchange",
            "segment",
            "symbol",
            "expiry",
            "strike",
            "option_type",
            name="uq_instruments_contract_identity",
        ),
    )
    op.create_index(
        "ix_instruments_exchange_symbol", "instruments", ["exchange", "symbol"], unique=False
    )

    op.create_table(
        "bars",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("instrument_id", sa.String(length=128), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("high", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("low", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("close", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=True),
        sa.Column("is_final", sa.Boolean(), nullable=False),
        sa.Column("quality", sa.String(length=16), nullable=False),
        sa.CheckConstraint("high >= low", name="ck_bars_high_gte_low"),
        sa.CheckConstraint("high >= open AND high >= close", name="ck_bars_high_gte_prices"),
        sa.CheckConstraint("low <= open AND low <= close", name="ck_bars_low_lte_prices"),
        sa.CheckConstraint("volume >= 0", name="ck_bars_non_negative_volume"),
        sa.CheckConstraint(
            "quality IN ('VALID', 'DEGRADED', 'STALE', 'INVALID')", name="ck_bars_quality"
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"], ["instruments.instrument_id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "instrument_id", "timeframe", "event_time", "source", name="uq_bars_point_in_time"
        ),
    )
    op.create_index(
        "ix_bars_instrument_timeframe_event",
        "bars",
        ["instrument_id", "timeframe", "event_time"],
        unique=False,
    )
    op.create_index("ix_bars_event_time", "bars", ["event_time"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bars_event_time", table_name="bars")
    op.drop_index("ix_bars_instrument_timeframe_event", table_name="bars")
    op.drop_table("bars")
    op.drop_index("ix_instruments_exchange_symbol", table_name="instruments")
    op.drop_table("instruments")
