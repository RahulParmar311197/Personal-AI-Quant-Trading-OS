from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.market_data.technical import TechnicalFeatures
from app.regime.engine import RegimeConfig, RegimeEngine

UTC = timezone.utc


def features(*, returns: Decimal | None, ema: Decimal | None, close: Decimal = Decimal("100"), range_pct: Decimal | None = Decimal("0.005")) -> TechnicalFeatures:
    return TechnicalFeatures(
        event_time=datetime(2026, 1, 1, 9, 15, tzinfo=UTC),
        instrument_id="NSE:NIFTY",
        close=close,
        sma=ema,
        ema=ema,
        rsi=Decimal("55"),
        atr=Decimal("1"),
        macd=Decimal("0.1"),
        macd_signal=Decimal("0.05"),
        bollinger_mid=Decimal("100"),
        bollinger_upper=Decimal("102"),
        bollinger_lower=Decimal("98"),
        volume_sma=Decimal("1000"),
        returns=returns,
        range_pct=range_pct,
        body_pct=Decimal("0.003"),
        upper_wick_pct=Decimal("0.001"),
        lower_wick_pct=Decimal("0.001"),
    )


def test_uptrend_classification() -> None:
    result = RegimeEngine().classify(features(returns=Decimal("0.004"), ema=Decimal("99")))
    assert result.regime == "TREND_UP"
    assert result.confidence >= Decimal("0.5")


def test_downtrend_classification() -> None:
    result = RegimeEngine().classify(features(returns=Decimal("-0.004"), ema=Decimal("101")))
    assert result.regime == "TREND_DOWN"


def test_high_volatility_has_precedence() -> None:
    result = RegimeEngine().classify(
        features(returns=Decimal("0.004"), ema=Decimal("99"), range_pct=Decimal("0.025"))
    )
    assert result.regime == "HIGH_VOLATILITY"


def test_range_when_no_directional_threshold_is_met() -> None:
    result = RegimeEngine().classify(features(returns=Decimal("0.0005"), ema=Decimal("100")))
    assert result.regime == "RANGE"


def test_unknown_during_warmup() -> None:
    result = RegimeEngine().classify(features(returns=None, ema=None))
    assert result.regime == "UNKNOWN"
    assert result.confidence == Decimal("0")


def test_series_rejects_duplicate_or_non_monotonic_timestamps() -> None:
    first = features(returns=Decimal("0.001"), ema=Decimal("100"))
    second = TechnicalFeatures(**{**first.__dict__, "event_time": datetime(2026, 1, 1, 9, 14, tzinfo=UTC)})
    with pytest.raises(ValueError, match="strictly increasing"):
        RegimeEngine().classify_series([first, second])


def test_thresholds_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        RegimeConfig(trend_return_threshold=Decimal("0"))
