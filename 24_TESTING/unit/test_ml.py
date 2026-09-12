from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.market_data.contracts import HistoricalBar
from app.ml.contracts import MLFeatureRow, TrainingExample
from app.ml.evaluation import evaluate_predictions
from app.ml.labels import LabelConfig, generate_labels
from app.ml.models import MajorityClassBaseline
from app.ml.splits import chronological_split


def _bars(closes: list[str]) -> list[HistoricalBar]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        HistoricalBar(
            instrument_id="NIFTY50",
            timeframe="5m",
            event_time=start + timedelta(minutes=5 * i),
            open=Decimal(close), high=Decimal(close), low=Decimal(close), close=Decimal(close),
            volume=1000, source="test",
        )
        for i, close in enumerate(closes)
    ]


def _examples(n: int) -> list[TrainingExample]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        TrainingExample(
            MLFeatureRow(start + timedelta(minutes=i), "NIFTY50", {"x": Decimal(i)}),
            "LONG" if i % 2 == 0 else "SHORT",
        )
        for i in range(n)
    ]


def test_forward_labels_leave_unobservable_tail_unlabeled() -> None:
    labels = generate_labels(_bars(["100", "101", "102", "103"]), LabelConfig(horizon_bars=2, return_threshold=Decimal("0.01")))
    assert labels == ["LONG", "LONG", None, None]


def test_labels_reject_non_chronological_bars() -> None:
    bars = _bars(["100", "101"])
    bars[1] = bars[0].model_copy(update={"event_time": bars[0].event_time})
    with pytest.raises(ValueError, match="strictly increasing"):
        generate_labels(bars)


def test_split_is_chronological_and_embargoes_partition_edges() -> None:
    split = chronological_split(_examples(20), embargo_bars=2)
    assert [x.row.features["x"] for x in split.train][-1] == Decimal("9")
    assert [x.row.features["x"] for x in split.validation] == [Decimal("12"), Decimal("13")]
    assert split.test[0].row.features["x"] == Decimal("16")


def test_split_rejects_shuffled_examples() -> None:
    examples = _examples(10)
    examples[2], examples[3] = examples[3], examples[2]
    with pytest.raises(ValueError, match="strictly chronological"):
        chronological_split(examples)


def test_majority_baseline_is_deterministic() -> None:
    model = MajorityClassBaseline()
    model.fit([{"x": Decimal("1")}] * 3, ["LONG", "LONG", "SHORT"])
    probabilities = model.predict_proba({"x": Decimal("9")})
    assert probabilities["LONG"] == Decimal(2) / Decimal(3)
    assert probabilities["SHORT"] == Decimal(1) / Decimal(3)
    assert probabilities["NEUTRAL"] == Decimal(0)


def test_evaluation_reports_accuracy_and_probabilistic_metrics() -> None:
    metrics = evaluate_predictions(
        ["LONG", "SHORT"],
        [
            {"LONG": Decimal("0.9"), "SHORT": Decimal("0.1"), "NEUTRAL": Decimal("0")},
            {"LONG": Decimal("0.2"), "SHORT": Decimal("0.8"), "NEUTRAL": Decimal("0")},
        ],
    )
    assert metrics.accuracy == Decimal("1")
    assert metrics.brier_score > 0
    assert metrics.log_loss > 0
