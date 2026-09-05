"""AtmosSim ML baseline benchmarking package."""

from .splits import OPERATIONAL_FEATURES, IDENTIFIER_COLUMNS, BenchmarkDataLoader
from .preprocessing import MLDataPreprocessor
from .baselines import (
    BaseBaselineModel,
    PersistenceBaseline,
    LinearRegressionBaseline,
    RidgeBaseline,
    RandomForestBaseline,
    XGBoostBaseline,
    LightGBMBaseline,
    CatBoostBaseline,
)
from .metrics import (
    mean_absolute_error,
    root_mean_squared_error,
    r2_score,
    mean_bias,
    normalized_rmse,
    median_absolute_error,
    p90_absolute_error,
    pearson_correlation,
    compute_all_metrics,
)
from .evaluation import ModelEvaluator, SEASONS
from .diagnostics import generate_all_diagnostics

__all__ = [
    "OPERATIONAL_FEATURES",
    "IDENTIFIER_COLUMNS",
    "BenchmarkDataLoader",
    "MLDataPreprocessor",
    "BaseBaselineModel",
    "PersistenceBaseline",
    "LinearRegressionBaseline",
    "RidgeBaseline",
    "RandomForestBaseline",
    "XGBoostBaseline",
    "LightGBMBaseline",
    "CatBoostBaseline",
    "mean_absolute_error",
    "root_mean_squared_error",
    "r2_score",
    "mean_bias",
    "normalized_rmse",
    "median_absolute_error",
    "p90_absolute_error",
    "pearson_correlation",
    "compute_all_metrics",
    "ModelEvaluator",
    "SEASONS",
    "generate_all_diagnostics",
]
