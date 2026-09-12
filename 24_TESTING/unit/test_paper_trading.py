from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.paper_trading.engine import PaperExecutionConfig, PaperTradingEngine


def ts(second: int) -> datetime:
    return datetime(2026, 1, 1, 9, 15, second, tzinfo=timezone.utc)


def test_market_order_fills_with_adverse_slippage_and_fee() -> None:
    engine = PaperTradingEngine(
        Decimal("100000"),
        PaperExecutionConfig(fee_bps=Decimal("10"), slippage_bps=Decimal("5")),
    )
    fill = engine.submit_market_order("NIFTY", "LONG", Decimal("2"), ts(0), Decimal("100"))
    assert fill.price == Decimal("100.05")
    assert fill.fee == Decimal("0.20010")
    assert engine.account.positions[0].quantity == Decimal("2")


def test_opposite_order_realizes_pnl() -> None:
    engine = PaperTradingEngine(Decimal("100000"))
    engine.submit_market_order("NIFTY", "LONG", Decimal("2"), ts(0), Decimal("100"))
    engine.submit_market_order("NIFTY", "SHORT", Decimal("2"), ts(1), Decimal("110"))
    assert engine.account.positions == ()
    assert engine.account.realized_pnl == Decimal("20")


def test_duplicate_client_order_id_is_rejected() -> None:
    engine = PaperTradingEngine(Decimal("100000"))
    engine.submit_market_order("NIFTY", "LONG", Decimal("1"), ts(0), Decimal("100"), "client-1")
    with pytest.raises(ValueError, match="duplicate order id"):
        engine.submit_market_order("NIFTY", "LONG", Decimal("1"), ts(1), Decimal("101"), "client-1")


def test_events_cannot_move_backwards() -> None:
    engine = PaperTradingEngine(Decimal("100000"))
    engine.submit_market_order("NIFTY", "LONG", Decimal("1"), ts(2), Decimal("100"))
    with pytest.raises(ValueError, match="chronological"):
        engine.submit_market_order("NIFTY", "SHORT", Decimal("1"), ts(1), Decimal("101"))


def test_mark_to_market_and_equity() -> None:
    engine = PaperTradingEngine(Decimal("100000"))
    engine.submit_market_order("NIFTY", "LONG", Decimal("10"), ts(0), Decimal("100"))
    assert engine.mark_to_market("NIFTY", Decimal("105")) == Decimal("50")
    assert engine.equity({"NIFTY": Decimal("105")}) == Decimal("99950")


def test_invalid_order_is_rejected() -> None:
    engine = PaperTradingEngine(Decimal("100000"))
    with pytest.raises(ValueError):
        engine.submit_market_order("NIFTY", "LONG", Decimal("0"), ts(0), Decimal("100"))
