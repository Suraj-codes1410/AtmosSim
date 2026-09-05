"""Unit tests for ML benchmark evaluator, extremes, and generalization metrics."""

import numpy as np
import pandas as pd
import pytest

from atmosim.ml.evaluation import ModelEvaluator


@pytest.fixture
def evaluator_fixture():
    np.random.seed(42)
    y_train = np.linspace(10.0, 100.0, 100)
    evaluator = ModelEvaluator(y_train=y_train)
    return evaluator


def test_evaluator_thresholds(evaluator_fixture):
    th = evaluator_fixture.extreme_thresholds
    assert "top_10_percent" in th
    assert "top_5_percent" in th
    assert "top_1_percent" in th
    assert th["top_10_percent"] < th["top_5_percent"] < th["top_1_percent"]


def test_evaluate_extremes(evaluator_fixture):
    y_test = np.array([10.0, 20.0, 85.0, 95.0, 100.0])
    y_pred = np.array([12.0, 19.0, 80.0, 96.0, 98.0])

    res = evaluator_fixture.evaluate_extremes(y_test, y_pred)
    assert "top_10_percent" in res
    assert "top_5_percent" in res
    assert "top_1_percent" in res
    assert res["top_10_percent"]["sample_count"] > 0
    assert not np.isnan(res["top_10_percent"]["rmse"])


def test_evaluate_seasons(evaluator_fixture):
    # Timestamps in January (Winter)
    ts = pd.date_range("2020-01-01", periods=10, freq="h")
    y_true = np.ones(10) * 20.0
    y_pred = np.ones(10) * 22.0

    seasons_res = evaluator_fixture.evaluate_seasons(y_true, y_pred, ts)
    assert "winter" in seasons_res
    assert seasons_res["winter"]["status"] == "VALID"
    assert seasons_res["monsoon"]["status"] == "N/A — insufficient observations"


def test_generalization_gaps(evaluator_fixture):
    val_metrics = {"rmse": 10.0, "mae": 8.0, "r2": 0.85}
    test_metrics = {"rmse": 12.0, "mae": 9.5, "r2": 0.80}
    cross_metrics = {"rmse": 15.0, "mae": 11.5, "r2": 0.70}

    temp_gap = evaluator_fixture.compute_temporal_generalization(val_metrics, test_metrics)
    assert temp_gap["delta_rmse"] == pytest.approx(2.0)
    assert temp_gap["delta_mae"] == pytest.approx(1.5)
    assert temp_gap["delta_r2"] == pytest.approx(0.05)

    geo_gap = evaluator_fixture.compute_geographic_generalization(test_metrics, cross_metrics)
    assert geo_gap["gap_rmse"] == pytest.approx(3.0)
    assert geo_gap["gap_mae"] == pytest.approx(2.0)
    assert geo_gap["gap_r2"] == pytest.approx(0.10)
