"""ML feature preprocessing pipelines for AtmosSim baselines.

Enforces strict fitting on the training split only. Provides tailored transforms
for linear models (one-hot encoding + standard scaling + imputation) and tree-based
models (ordinal encoding + native scale preservation).
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer

from .splits import OPERATIONAL_FEATURES

STABILITY_CLASSES: List[str] = ["A", "B", "C", "D", "E", "F"]
STABILITY_ORDINAL_MAP: Dict[str, int] = {cls: idx for idx, cls in enumerate(STABILITY_CLASSES, start=1)}


class MLDataPreprocessor:
    """Encapsulates feature transformations fit strictly on training data."""

    def __init__(self) -> None:
        self.is_fitted: bool = False
        self.numeric_features: List[str] = [f for f in OPERATIONAL_FEATURES if f != "stability_class"]
        self.categorical_features: List[str] = ["stability_class"]

        # Linear model components
        self.num_imputer: SimpleImputer = SimpleImputer(strategy="median")
        self.scaler: StandardScaler = StandardScaler()
        self.ohe: OneHotEncoder = OneHotEncoder(
            categories=[STABILITY_CLASSES],
            sparse_output=False,
            handle_unknown="ignore",
        )
        self.linear_feature_names: List[str] = []

    def fit(self, X_train: pd.DataFrame) -> MLDataPreprocessor:
        """Fit all transformers strictly on the training features."""
        # 1. Fit numerical imputer and scaler on numeric features
        X_num = X_train[self.numeric_features]
        X_num_imp = self.num_imputer.fit_transform(X_num)
        self.scaler.fit(X_num_imp)

        # 2. Fit one-hot encoder on categorical stability class
        X_cat = X_train[self.categorical_features]
        self.ohe.fit(X_cat)

        ohe_cols = [f"stability_{cls}" for cls in STABILITY_CLASSES]
        self.linear_feature_names = list(self.numeric_features) + ohe_cols

        self.is_fitted = True
        return self

    def transform_linear(self, X: pd.DataFrame) -> np.ndarray:
        """Transform features for linear / Ridge regression models."""
        if not self.is_fitted:
            raise RuntimeError("Preprocessor must be fit on X_train before transform.")

        X_num = X[self.numeric_features]
        X_num_imp = self.num_imputer.transform(X_num)
        X_num_scaled = self.scaler.transform(X_num_imp)

        X_cat = X[self.categorical_features]
        X_cat_ohe = self.ohe.transform(X_cat)

        return np.hstack([X_num_scaled, X_cat_ohe])

    def transform_tree(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform features for tree-based models (RF, XGBoost, LightGBM, CatBoost).

        Preserves unscaled numerical values and ordinally encodes categorical stability class.
        """
        if not self.is_fitted:
            raise RuntimeError("Preprocessor must be fit on X_train before transform.")

        X_tree = X.copy()
        # Ordinal encoding for stability_class
        X_tree["stability_class"] = X_tree["stability_class"].map(
            lambda v: STABILITY_ORDINAL_MAP.get(str(v).upper(), 4)  # Default 'D' (4)
        ).astype(int)

        # Impute missing numeric features if any
        for col in self.numeric_features:
            if X_tree[col].isna().any():
                col_idx = self.numeric_features.index(col)
                fill_val = self.num_imputer.statistics_[col_idx]
                X_tree[col] = X_tree[col].fillna(fill_val)

        return X_tree


__all__ = [
    "STABILITY_CLASSES",
    "STABILITY_ORDINAL_MAP",
    "MLDataPreprocessor",
]
