"""Evaluation metrics for AtmosSim ML baselines.

Implements regression metrics and physical error diagnostics:
- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)
- R2 (Coefficient of Determination)
- Mean Bias (mean(y_pred - y_true))
- Normalized RMSE (RMSE / mean(y_true))
- Median Absolute Error
- P90 Absolute Error
- Pearson Correlation (with safe handling of constant predictions)
"""

from __future__ import annotations
import numpy as np
from typing import Dict, Any


def mean_absolute_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute Mean Absolute Error."""
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    if len(y_t) == 0:
        return float("nan")
    return float(np.mean(np.abs(y_t - y_p)))


def root_mean_squared_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute Root Mean Squared Error."""
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    if len(y_t) == 0:
        return float("nan")
    return float(np.sqrt(np.mean((y_t - y_p) ** 2)))


def r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute Coefficient of Determination (R^2)."""
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    if len(y_t) < 2:
        return float("nan")
    ss_res = np.sum((y_t - y_p) ** 2)
    ss_tot = np.sum((y_t - np.mean(y_t)) ** 2)
    if ss_tot == 0.0:
        return 1.0 if ss_res == 0.0 else 0.0
    return float(1.0 - (ss_res / ss_tot))


def mean_bias(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute Mean Bias Error (predicted - true)."""
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    if len(y_t) == 0:
        return float("nan")
    return float(np.mean(y_p - y_t))


def normalized_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute Normalized RMSE (RMSE / mean(y_true))."""
    rmse = root_mean_squared_error(y_true, y_pred)
    y_t = np.asarray(y_true, dtype=np.float64)
    mean_true = float(np.mean(y_t)) if len(y_t) > 0 else 0.0
    if mean_true == 0.0:
        return float("nan")
    return float(rmse / mean_true)


def median_absolute_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute Median Absolute Error."""
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    if len(y_t) == 0:
        return float("nan")
    return float(np.median(np.abs(y_t - y_p)))


def p90_absolute_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute 90th percentile of Absolute Error."""
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    if len(y_t) == 0:
        return float("nan")
    return float(np.percentile(np.abs(y_t - y_p), 90))


def pearson_correlation(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Compute Pearson Correlation coefficient safely."""
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    if len(y_t) < 2:
        return float("nan")
    std_t = np.std(y_t)
    std_p = np.std(y_p)
    if std_t == 0.0 or std_p == 0.0:
        return 0.0
    corr = np.corrcoef(y_t, y_p)[0, 1]
    return float(corr) if np.isfinite(corr) else 0.0


def compute_all_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate all standard regression and physical diagnostics."""
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)
    return {
        "mae": mean_absolute_error(y_t, y_p),
        "rmse": root_mean_squared_error(y_t, y_p),
        "r2": r2_score(y_t, y_p),
        "mean_bias": mean_bias(y_t, y_p),
        "normalized_rmse": normalized_rmse(y_t, y_p),
        "median_ae": median_absolute_error(y_t, y_p),
        "p90_ae": p90_absolute_error(y_t, y_p),
        "correlation": pearson_correlation(y_t, y_p),
        "sample_count": len(y_t),
    }


__all__ = [
    "mean_absolute_error",
    "root_mean_squared_error",
    "r2_score",
    "mean_bias",
    "normalized_rmse",
    "median_absolute_error",
    "p90_absolute_error",
    "pearson_correlation",
    "compute_all_metrics",
]
