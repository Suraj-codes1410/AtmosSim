"""Evaluation protocol, extreme-value analysis, and generalization auditing for ML baselines."""

from __future__ import annotations
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from .metrics import compute_all_metrics, mean_absolute_error, root_mean_squared_error, mean_bias, pearson_correlation

# Meteorological / Climatological seasonal mapping
SEASONS: Dict[str, List[int]] = {
    "winter": [12, 1, 2],
    "pre_monsoon_summer": [3, 4, 5],
    "monsoon": [6, 7, 8],
    "post_monsoon": [9, 10, 11],
}


class ModelEvaluator:
    """Orchestrates comprehensive multi-split, extreme-value, and generalization benchmarks."""

    def __init__(self, y_train: np.ndarray) -> None:
        self.y_train = np.asarray(y_train, dtype=np.float64)
        # Training-derived extreme thresholds (strictly no test leakage)
        self.extreme_thresholds = {
            "top_10_percent": float(np.percentile(self.y_train, 90)),
            "top_5_percent": float(np.percentile(self.y_train, 95)),
            "top_1_percent": float(np.percentile(self.y_train, 99)),
        }

    def evaluate_split(
        self, y_true: np.ndarray, y_pred: np.ndarray
    ) -> Dict[str, float]:
        """Compute standard regression metrics on a full split."""
        return compute_all_metrics(y_true, y_pred)

    def evaluate_extremes(
        self, y_true: np.ndarray, y_pred: np.ndarray
    ) -> Dict[str, Dict[str, Any]]:
        """Evaluate performance on high-concentration subsets using training thresholds."""
        y_t = np.asarray(y_true, dtype=np.float64)
        y_p = np.asarray(y_pred, dtype=np.float64)

        results = {}
        for pct_name, threshold in self.extreme_thresholds.items():
            mask = y_t >= threshold
            count = int(np.sum(mask))
            if count == 0:
                results[pct_name] = {
                    "threshold_value": threshold,
                    "sample_count": 0,
                    "mae": float("nan"),
                    "rmse": float("nan"),
                    "bias": float("nan"),
                    "correlation": float("nan"),
                    "status": "N/A — insufficient observations",
                }
            else:
                sub_true = y_t[mask]
                sub_pred = y_p[mask]
                results[pct_name] = {
                    "threshold_value": threshold,
                    "sample_count": count,
                    "mae": mean_absolute_error(sub_true, sub_pred),
                    "rmse": root_mean_squared_error(sub_true, sub_pred),
                    "bias": mean_bias(sub_true, sub_pred),
                    "correlation": pearson_correlation(sub_true, sub_pred),
                    "status": "VALID",
                }
        return results

    def evaluate_seasons(
        self, y_true: np.ndarray, y_pred: np.ndarray, timestamps: pd.Series
    ) -> Dict[str, Dict[str, Any]]:
        """Evaluate performance stratified across climatological seasons."""
        y_t = np.asarray(y_true, dtype=np.float64)
        y_p = np.asarray(y_pred, dtype=np.float64)
        months = pd.DatetimeIndex(timestamps).month.values

        seasonal_results = {}
        for season_name, season_months in SEASONS.items():
            mask = np.isin(months, season_months)
            count = int(np.sum(mask))
            if count < 5:  # Insufficient samples threshold
                seasonal_results[season_name] = {
                    "sample_count": count,
                    "mae": float("nan"),
                    "rmse": float("nan"),
                    "r2": float("nan"),
                    "mean_bias": float("nan"),
                    "status": "N/A — insufficient observations",
                }
            else:
                sub_true = y_t[mask]
                sub_pred = y_p[mask]
                metrics = compute_all_metrics(sub_true, sub_pred)
                metrics["status"] = "VALID"
                seasonal_results[season_name] = metrics

        return seasonal_results

    def compute_temporal_generalization(
        self, val_metrics: Dict[str, float], test_metrics: Dict[str, float]
    ) -> Dict[str, float]:
        """Compute degradation between validation and test splits."""
        return {
            "delta_rmse": float(test_metrics["rmse"] - val_metrics["rmse"]),
            "delta_mae": float(test_metrics["mae"] - val_metrics["mae"]),
            "delta_r2": float(val_metrics["r2"] - test_metrics["r2"]),
        }

    def compute_geographic_generalization(
        self, test_metrics: Dict[str, float], cross_metrics: Dict[str, float]
    ) -> Dict[str, float]:
        """Compute geographic generalization gaps between test and cross-location holdout."""
        return {
            "gap_rmse": float(cross_metrics["rmse"] - test_metrics["rmse"]),
            "gap_mae": float(cross_metrics["mae"] - test_metrics["mae"]),
            "gap_r2": float(test_metrics["r2"] - cross_metrics["r2"]),
        }


__all__ = [
    "SEASONS",
    "ModelEvaluator",
]
