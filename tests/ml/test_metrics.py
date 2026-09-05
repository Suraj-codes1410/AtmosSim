"""Unit tests for ML regression and diagnostic metrics."""

import numpy as np
import pytest
from atmosim.ml.metrics import (
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


def test_metrics_perfect_predictions():
    y_true = np.array([10.0, 20.0, 30.0, 40.0])
    y_pred = np.array([10.0, 20.0, 30.0, 40.0])

    assert mean_absolute_error(y_true, y_pred) == 0.0
    assert root_mean_squared_error(y_true, y_pred) == 0.0
    assert r2_score(y_true, y_pred) == 1.0
    assert mean_bias(y_true, y_pred) == 0.0
    assert normalized_rmse(y_true, y_pred) == 0.0
    assert median_absolute_error(y_true, y_pred) == 0.0
    assert p90_absolute_error(y_true, y_pred) == 0.0
    assert pytest.approx(pearson_correlation(y_true, y_pred)) == 1.0


def test_metrics_known_errors():
    y_true = np.array([10.0, 20.0, 30.0])
    y_pred = np.array([12.0, 18.0, 34.0])  # diffs: +2, -2, +4

    assert mean_absolute_error(y_true, y_pred) == pytest.approx(8.0 / 3.0)
    assert root_mean_squared_error(y_true, y_pred) == pytest.approx(np.sqrt(24.0 / 3.0))
    assert mean_bias(y_true, y_pred) == pytest.approx(4.0 / 3.0)


def test_metrics_edge_cases_empty_and_zero_variance():
    # Empty
    assert np.isnan(mean_absolute_error(np.array([]), np.array([])))
    assert np.isnan(root_mean_squared_error(np.array([]), np.array([])))

    # Zero variance target
    y_true = np.array([5.0, 5.0, 5.0])
    y_pred = np.array([5.0, 5.0, 5.0])
    assert r2_score(y_true, y_pred) == 1.0
    assert pearson_correlation(y_true, y_pred) == 0.0  # safe handle

    # Zero mean target for nRMSE
    y_zero = np.array([0.0, 0.0])
    y_pred_z = np.array([1.0, 2.0])
    assert np.isnan(normalized_rmse(y_zero, y_pred_z))


def test_compute_all_metrics_dict():
    y_true = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    y_pred = np.array([11.0, 19.0, 31.0, 39.0, 51.0])
    m = compute_all_metrics(y_true, y_pred)
    assert "mae" in m
    assert "rmse" in m
    assert "r2" in m
    assert "mean_bias" in m
    assert "normalized_rmse" in m
    assert "median_ae" in m
    assert "p90_ae" in m
    assert "correlation" in m
    assert m["sample_count"] == 5
