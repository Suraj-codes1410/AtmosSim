"""Deterministic baseline models for AtmosSim Phase 7 benchmark.

Implements:
1. Persistence / Naive Baseline
2. Linear Regression
3. Ridge Regression
4. Random Forest
5. XGBoost
6. LightGBM
7. CatBoost
"""

from __future__ import annotations
import time
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
import lightgbm as lgb
import catboost as cb


class BaseBaselineModel:
    """Base interface for reproducible AtmosSim ML baselines."""

    name: str = "base"

    def __init__(self) -> None:
        self.is_fitted: bool = False
        self.fit_time_seconds: float = 0.0
        self.predict_time_seconds: float = 0.0

    def fit(self, X: Any, y: np.ndarray) -> BaseBaselineModel:
        raise NotImplementedError

    def predict(self, X: Any) -> np.ndarray:
        raise NotImplementedError

    def get_config(self) -> Dict[str, Any]:
        raise NotImplementedError


class PersistenceBaseline(BaseBaselineModel):
    """Naive persistence baseline.

    Under the frozen Phase 6 operational protocol, historical target PM2.5 values
    are excluded from the operational feature set. Therefore, this naive baseline
    learns the training distribution mean and predicts it constantly, representing
    the zero-signal naive reference benchmark.
    """

    name: str = "persistence"

    def __init__(self) -> None:
        super().__init__()
        self.mean_target: float = 0.0

    def fit(self, X: Any, y: np.ndarray) -> PersistenceBaseline:
        t0 = time.perf_counter()
        y_arr = np.asarray(y, dtype=np.float64)
        self.mean_target = float(np.mean(y_arr))
        self.fit_time_seconds = time.perf_counter() - t0
        self.is_fitted = True
        return self

    def predict(self, X: Any) -> np.ndarray:
        t0 = time.perf_counter()
        n_samples = len(X)
        preds = np.full(n_samples, self.mean_target, dtype=np.float64)
        self.predict_time_seconds = time.perf_counter() - t0
        return preds

    def get_config(self) -> Dict[str, Any]:
        return {
            "model_name": self.name,
            "strategy": "training_target_mean_persistence",
            "mean_target": self.mean_target,
        }


class LinearRegressionBaseline(BaseBaselineModel):
    """Ordinary Least Squares Linear Regression baseline."""

    name: str = "linear"

    def __init__(self, fit_intercept: bool = True) -> None:
        super().__init__()
        self.fit_intercept = fit_intercept
        self.model = LinearRegression(fit_intercept=self.fit_intercept)

    def fit(self, X: np.ndarray, y: np.ndarray) -> LinearRegressionBaseline:
        t0 = time.perf_counter()
        self.model.fit(X, y)
        self.fit_time_seconds = time.perf_counter() - t0
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        t0 = time.perf_counter()
        preds = self.model.predict(X)
        self.predict_time_seconds = time.perf_counter() - t0
        return np.asarray(preds, dtype=np.float64)

    def get_config(self) -> Dict[str, Any]:
        return {
            "model_name": self.name,
            "package": "sklearn.linear_model.LinearRegression",
            "fit_intercept": self.fit_intercept,
        }


class RidgeBaseline(BaseBaselineModel):
    """Ridge L2-regularized linear regression baseline."""

    name: str = "ridge"

    def __init__(self, alpha: float = 1.0, random_state: int = 42) -> None:
        super().__init__()
        self.alpha = float(alpha)
        self.random_state = random_state
        self.model = Ridge(alpha=self.alpha, random_state=self.random_state)

    def fit(self, X: np.ndarray, y: np.ndarray) -> RidgeBaseline:
        t0 = time.perf_counter()
        self.model.fit(X, y)
        self.fit_time_seconds = time.perf_counter() - t0
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        t0 = time.perf_counter()
        preds = self.model.predict(X)
        self.predict_time_seconds = time.perf_counter() - t0
        return np.asarray(preds, dtype=np.float64)

    def get_config(self) -> Dict[str, Any]:
        return {
            "model_name": self.name,
            "package": "sklearn.linear_model.Ridge",
            "alpha": self.alpha,
            "random_state": self.random_state,
        }


class RandomForestBaseline(BaseBaselineModel):
    """Deterministic Random Forest regressor baseline."""

    name: str = "random_forest"

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: Optional[int] = 12,
        min_samples_split: int = 2,
        min_samples_leaf: int = 1,
        max_features: str = "sqrt",
        random_state: int = 42,
    ) -> None:
        super().__init__()
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.max_features = max_features
        self.random_state = random_state

        self.model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_split=self.min_samples_split,
            min_samples_leaf=self.min_samples_leaf,
            max_features=self.max_features,
            random_state=self.random_state,
            n_jobs=-1,
        )

    def fit(self, X: Any, y: np.ndarray) -> RandomForestBaseline:
        t0 = time.perf_counter()
        self.model.fit(X, y)
        self.fit_time_seconds = time.perf_counter() - t0
        self.is_fitted = True
        return self

    def predict(self, X: Any) -> np.ndarray:
        t0 = time.perf_counter()
        preds = self.model.predict(X)
        self.predict_time_seconds = time.perf_counter() - t0
        return np.asarray(preds, dtype=np.float64)

    def get_config(self) -> Dict[str, Any]:
        return {
            "model_name": self.name,
            "package": "sklearn.ensemble.RandomForestRegressor",
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "min_samples_split": self.min_samples_split,
            "min_samples_leaf": self.min_samples_leaf,
            "max_features": self.max_features,
            "random_state": self.random_state,
        }


class XGBoostBaseline(BaseBaselineModel):
    """Deterministic XGBoost gradient boosted trees baseline."""

    name: str = "xgboost"

    def __init__(
        self,
        n_estimators: int = 100,
        learning_rate: float = 0.05,
        max_depth: int = 6,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        random_state: int = 42,
    ) -> None:
        super().__init__()
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.random_state = random_state

        self.model = xgb.XGBRegressor(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            max_depth=self.max_depth,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            random_state=self.random_state,
            objective="reg:squarederror",
            n_jobs=-1,
        )

    def fit(self, X: Any, y: np.ndarray) -> XGBoostBaseline:
        t0 = time.perf_counter()
        self.model.fit(X, y)
        self.fit_time_seconds = time.perf_counter() - t0
        self.is_fitted = True
        return self

    def predict(self, X: Any) -> np.ndarray:
        t0 = time.perf_counter()
        preds = self.model.predict(X)
        self.predict_time_seconds = time.perf_counter() - t0
        return np.asarray(preds, dtype=np.float64)

    def get_config(self) -> Dict[str, Any]:
        return {
            "model_name": self.name,
            "package": "xgboost.XGBRegressor",
            "package_version": xgb.__version__,
            "objective": "reg:squarederror",
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "max_depth": self.max_depth,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "random_state": self.random_state,
        }


class LightGBMBaseline(BaseBaselineModel):
    """Deterministic LightGBM gradient boosted trees baseline."""

    name: str = "lightgbm"

    def __init__(
        self,
        n_estimators: int = 100,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        max_depth: int = -1,
        subsample: float = 0.8,
        random_state: int = 42,
    ) -> None:
        super().__init__()
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.max_depth = max_depth
        self.subsample = subsample
        self.random_state = random_state

        self.model = lgb.LGBMRegressor(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            num_leaves=self.num_leaves,
            max_depth=self.max_depth,
            subsample=self.subsample,
            random_state=self.random_state,
            objective="regression",
            verbosity=-1,
            n_jobs=-1,
        )

    def fit(self, X: Any, y: np.ndarray) -> LightGBMBaseline:
        t0 = time.perf_counter()
        self.model.fit(X, y)
        self.fit_time_seconds = time.perf_counter() - t0
        self.is_fitted = True
        return self

    def predict(self, X: Any) -> np.ndarray:
        t0 = time.perf_counter()
        preds = self.model.predict(X)
        self.predict_time_seconds = time.perf_counter() - t0
        return np.asarray(preds, dtype=np.float64)

    def get_config(self) -> Dict[str, Any]:
        return {
            "model_name": self.name,
            "package": "lightgbm.LGBMRegressor",
            "package_version": lgb.__version__,
            "objective": "regression",
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "max_depth": self.max_depth,
            "subsample": self.subsample,
            "random_state": self.random_state,
        }


class CatBoostBaseline(BaseBaselineModel):
    """Deterministic CatBoost gradient boosted trees baseline."""

    name: str = "catboost"

    def __init__(
        self,
        iterations: int = 100,
        learning_rate: float = 0.05,
        depth: int = 6,
        random_seed: int = 42,
    ) -> None:
        super().__init__()
        self.iterations = iterations
        self.learning_rate = learning_rate
        self.depth = depth
        self.random_seed = random_seed

        self.model = cb.CatBoostRegressor(
            iterations=self.iterations,
            learning_rate=self.learning_rate,
            depth=self.depth,
            random_seed=self.random_seed,
            loss_function="RMSE",
            verbose=0,
            thread_count=-1,
        )

    def fit(self, X: Any, y: np.ndarray) -> CatBoostBaseline:
        t0 = time.perf_counter()
        self.model.fit(X, y)
        self.fit_time_seconds = time.perf_counter() - t0
        self.is_fitted = True
        return self

    def predict(self, X: Any) -> np.ndarray:
        t0 = time.perf_counter()
        preds = self.model.predict(X)
        self.predict_time_seconds = time.perf_counter() - t0
        return np.asarray(preds, dtype=np.float64)

    def get_config(self) -> Dict[str, Any]:
        return {
            "model_name": self.name,
            "package": "catboost.CatBoostRegressor",
            "package_version": cb.__version__,
            "loss_function": "RMSE",
            "iterations": self.iterations,
            "learning_rate": self.learning_rate,
            "depth": self.depth,
            "random_seed": self.random_seed,
        }


__all__ = [
    "BaseBaselineModel",
    "PersistenceBaseline",
    "LinearRegressionBaseline",
    "RidgeBaseline",
    "RandomForestBaseline",
    "XGBoostBaseline",
    "LightGBMBaseline",
    "CatBoostBaseline",
]
