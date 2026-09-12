"""Point-in-time-safe machine-learning research contracts and utilities."""

from app.ml.contracts import MLFeatureRow, ModelMetadata, Prediction, TrainingExample
from app.ml.evaluation import ClassificationMetrics, evaluate_predictions
from app.ml.labels import LabelConfig, MLLabel, generate_labels
from app.ml.models import MajorityClassBaseline
from app.ml.splits import DatasetSplit, chronological_split

__all__ = [
    "ClassificationMetrics",
    "DatasetSplit",
    "LabelConfig",
    "MLFeatureRow",
    "MLLabel",
    "MajorityClassBaseline",
    "ModelMetadata",
    "Prediction",
    "TrainingExample",
    "chronological_split",
    "evaluate_predictions",
    "generate_labels",
]
