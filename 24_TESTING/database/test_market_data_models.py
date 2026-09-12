from datetime import date, datetime, timezone
from decimal import Decimal

from app.core.database import Base
from app.models.market_data import Bar, Instrument


def test_market_data_tables_are_registered() -> None:
    assert "instruments" in Base.metadata.tables
    assert "bars" in Base.metadata.tables


def test_instrument_has_canonical_identity_columns() -> None:
    columns = Instrument.__table__.c
    for name in (
        "instrument_id",
        "exchange",
        "segment",
        "symbol",
        "provider_symbol",
        "currency",
        "timezone",
        "asset_type",
        "expiry",
        "strike",
        "option_type",
    ):
        assert name in columns


def test_bar_has_point_in_time_and_ohlcv_columns() -> None:
    columns = Bar.__table__.c
    for name in (
        "instrument_id",
        "timeframe",
        "event_time",
        "ingested_at",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source",
        "sequence",
        "is_final",
        "quality",
    ):
        assert name in columns


def test_bar_constraints_cover_market_data_invariants() -> None:
    constraint_names = {constraint.name for constraint in Bar.__table__.constraints}
    assert {
        "ck_bars_high_gte_low",
        "ck_bars_high_gte_prices",
        "ck_bars_low_lte_prices",
        "ck_bars_non_negative_volume",
        "ck_bars_quality",
        "uq_bars_point_in_time",
    } <= constraint_names


def test_instrument_constraints_cover_contract_identity() -> None:
    constraint_names = {constraint.name for constraint in Instrument.__table__.constraints}
    assert {
        "ck_instruments_asset_type",
        "ck_instruments_option_type",
        "ck_instruments_option_fields",
        "uq_instruments_contract_identity",
    } <= constraint_names


def test_canonical_bar_values_support_exact_price_storage() -> None:
    bar = Bar(
        instrument_id="NSE:NIFTY50",
        timeframe="1m",
        event_time=datetime(2026, 9, 12, 9, 15, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 9, 12, 9, 15, 1, tzinfo=timezone.utc),
        open=Decimal("25000.10"),
        high=Decimal("25010.20"),
        low=Decimal("24995.00"),
        close=Decimal("25005.30"),
        volume=1000,
        source="test",
        is_final=True,
        quality="VALID",
    )
    assert bar.high >= bar.open
    assert bar.high >= bar.close
    assert bar.low <= bar.open
    assert bar.low <= bar.close
    assert bar.volume >= 0
    assert bar.event_time.tzinfo is not None


def test_option_identity_can_represent_expiry_strike_and_type() -> None:
    instrument = Instrument(
        instrument_id="NSE:NIFTY-2026-09-24-25000-CE",
        exchange="NSE",
        segment="FO",
        symbol="NIFTY",
        currency="INR",
        timezone="Asia/Kolkata",
        asset_type="OPTION",
        expiry=date(2026, 9, 24),
        strike=Decimal("25000"),
        option_type="CE",
    )
    assert instrument.expiry == date(2026, 9, 24)
    assert instrument.strike == Decimal("25000")
    assert instrument.option_type == "CE"
