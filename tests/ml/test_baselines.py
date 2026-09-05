"""Unit tests for ML baseline models."""

import numpy as np
import pandas as pd
import pytest

from atmosim.ml.baselines import (
    PersistenceBaseline,
    LinearRegressionBaseline,
    RidgeBaseline,
    RandomForestBaseline,
    XGBoostBaseline,
    LightGBMBaseline,
    CatBoostBaseline,
)


@pytest.fixture
def synthetic_data():
    np.random.seed(42)
    X = np.random.randn(40, 5)
    y = 2.0 * X[:, 0] - 1.5 * X[:, 1] + 10.0 + np.random.normal(0, 0.1, size=40)
    return X, y


def test_persistence_baseline(synthetic_data):
    X, y = synthetic_data
    model = PersistenceBaseline()
    model.fit(X, y)
    assert model.is_fitted
    preds = model.predict(X)
    assert len(preds) == len(y)
    assert np.allclose(preds, np.mean(y))
    cfg = model.get_config()
    assert cfg["model_name"] == "persistence"


def test_linear_and_ridge_baselines(synthetic_data):
    X, y = synthetic_data
    lin = LinearRegressionBaseline().fit(X, y)
    ridge = RidgeBaseline(alpha=1.0).fit(X, y)

    p_lin = lin.predict(X)
    p_ridge = ridge.predict(X)

    assert len(p_lin) == len(y)
    assert len(p_ridge) == len(y)
    assert lin.fit_time_seconds > 0.0
    assert ridge.predict_time_seconds > 0.0


def test_tree_baselines_determinism(synthetic_data):
    X, y = synthetic_data
    models = [
        RandomForestBaseline(n_estimators=10, max_depth=3, random_state=42),
        XGBoostBaseline(n_estimators=10, max_depth=3, random_state=42),
        LightGBMBaseline(n_estimators=10, num_leaves=7, max_depth=3, random_state=42),
        CatBoostBaseline(iterations=10, depth=3, random_seed=42),
    ]

    for m in models:
        m.fit(X, y)
        assert m.is_fitted
        preds1 = m.predict(X)
        preds2 = m.predict(X)
        assert np.allclose(preds1, preds2), f"{m.name} is not deterministic across inference"
        assert len(preds1) == len(y)
        cfg = m.get_config()
        assert cfg["model_name"] == m.name
