from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.market_data.contracts import HistoricalBar
from app.market_data.smc_ict import detect_equal_liquidity, detect_fair_value_gaps, detect_order_blocks, premium_discount

UTC = timezone.utc
BASE = datetime(2026, 9, 12, 9, 15, tzinfo=UTC)


def bar(i: int, open_: str, high: str, low: str, close: str) -> HistoricalBar:
    return HistoricalBar(
        instrument_id="NSE:NIFTY50", timeframe="5m",
        event_time=BASE + timedelta(minutes=5 * i), open=Decimal(open_),
        high=Decimal(high), low=Decimal(low), close=Decimal(close), volume=100,
        source="test", is_final=True,
    )


def test_bullish_fvg_is_detected_without_future_data() -> None:
    result = detect_fair_value_gaps([
        bar(0, "100", "101", "99", "100"),
        bar(1, "100", "105", "100", "104"),
        bar(2, "106", "108", "105", "107"),
    ])
    assert len(result) == 1
    assert result[0].direction == "BULLISH"
    assert result[0].lower == Decimal("101")
    assert result[0].upper == Decimal("105")


def test_equal_highs_create_buy_side_liquidity_pool() -> None:
    bars = [
        bar(0, "100", "105", "98", "100"),
        bar(1, "100", "110", "99", "108"),
        bar(2, "104", "104", "96", "100"),
        bar(3, "100", "110.02", "98", "108"),
        bar(4, "105", "105", "97", "101"),
    ]
    pools = detect_equal_liquidity(bars, tolerance=Decimal("0.001"))
    assert any(pool.side == "BUY_SIDE" for pool in pools)


def test_premium_discount_uses_trailing_range() -> None:
    bars = [bar(i, "100", str(100 + i), str(99 + i), str(100 + i)) for i in range(5)]
    result = premium_discount(bars, lookback=5)
    assert result is not None
    assert result.zone == "PREMIUM"
    assert result.equilibrium == Decimal("101")


def test_displacement_order_block_is_deterministic() -> None:
    bars = [bar(i, "100", "101", "99", "100") for i in range(12)]
    bars[-2] = bar(10, "100", "101", "98", "99")
    bars[-1] = bar(11, "99", "110", "98", "109")
    result = detect_order_blocks(bars, displacement_factor=Decimal("1.5"), range_period=10)
    assert result
    assert result[-1].direction == "BULLISH"
