"""Unit tests for ML feature preprocessor."""

import numpy as np
import pandas as pd
import pytest
from atmosim.ml.preprocessing import MLDataPreprocessor
from atmosim.ml.splits import OPERATIONAL_FEATURES


@pytest.fixture
def sample_feature_dfs():
    np.random.seed(42)
    n_train = 50
    n_test = 20

    def make_X(n):
        data = {f: np.random.randn(n) for f in OPERATIONAL_FEATURES if f != "stability_class"}
        data["stability_class"] = np.random.choice(["A", "D", "F"], size=n)
        return pd.DataFrame(data)

    return make_X(n_train), make_X(n_test)


def test_preprocessor_fit_and_transform(sample_feature_dfs):
    X_train, X_test = sample_feature_dfs
    pre = MLDataPreprocessor()

    # Transforming before fit raises
    with pytest.raises(RuntimeError):
        pre.transform_linear(X_train)

    pre.fit(X_train)
    assert pre.is_fitted

    # Linear transform
    X_tr_lin = pre.transform_linear(X_train)
    X_te_lin = pre.transform_linear(X_test)
    assert isinstance(X_tr_lin, np.ndarray)
    assert X_tr_lin.shape[0] == len(X_train)
    # Check that scaled training data has approx zero mean
    num_cols = len(pre.numeric_features)
    assert np.allclose(np.mean(X_tr_lin[:, :num_cols], axis=0), 0.0, atol=1e-7)

    # Tree transform
    X_tr_tree = pre.transform_tree(X_train)
    X_te_tree = pre.transform_tree(X_test)
    assert isinstance(X_tr_tree, pd.DataFrame)
    assert X_tr_tree["stability_class"].dtype in [int, np.int64, np.int32]
    assert set(X_tr_tree["stability_class"].unique()).issubset({1, 2, 3, 4, 5, 6})


def test_preprocessor_handles_nan_imputation(sample_feature_dfs):
    X_train, X_test = sample_feature_dfs
    X_train.loc[0, "wind_speed"] = np.nan
    X_test.loc[0, "wind_speed"] = np.nan

    pre = MLDataPreprocessor().fit(X_train)
    X_lin = pre.transform_linear(X_test)
    assert not np.isnan(X_lin).any()

    X_tree = pre.transform_tree(X_test)
    assert not X_tree["wind_speed"].isna().any()
