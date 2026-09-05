"""Dataset loading, validation, and feature/target separation for AtmosSim ML baselines."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, Tuple, List, Union
import pandas as pd
import numpy as np

# Canonical operational features from Phase 6
OPERATIONAL_FEATURES: List[str] = [
    "wind_speed",
    "wind_u",
    "wind_v",
    "temperature",
    "relative_humidity",
    "surface_pressure",
    "pblh",
    "stability_class",
    "hour",
    "day_of_week",
    "month",
    "sin_hour",
    "cos_hour",
    "wind_speed_mean_3h",
    "temperature_mean_6h",
]

IDENTIFIER_COLUMNS: List[str] = [
    "sample_id",
    "timestamp",
    "region_id",
    "location_id",
]

FORBIDDEN_SIMULATOR_STATE: List[str] = [
    "puff_x", "puff_y", "puff_z", "puff_mass", "puff_age",
    "sigma_x", "sigma_y", "sigma_z", "concentration_field",
    "transported_mass", "trajectory_state", "source_transport_distance",
    "raw_concentration_pm25", "concentration_pm25",
]


class BenchmarkDataLoader:
    """Loads, validates, and partitions the Phase 6 benchmark dataset release."""

    def __init__(
        self,
        dataset_dir: Union[str, Path] = "artifacts/benchmark_dataset/v1.0",
        expected_dataset_version: str = "v1.0",
    ) -> None:
        self.dataset_dir = Path(dataset_dir)
        self.expected_version = expected_dataset_version
        self.metadata = self._load_metadata()
        self.target_name = self.metadata.get("target", "target_pm25")

    def _load_metadata(self) -> Dict[str, Any]:
        meta_path = self.dataset_dir / "metadata.json"
        if not meta_path.is_file():
            raise FileNotFoundError(f"Metadata file missing: {meta_path}")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        ver = meta.get("dataset_version")
        if ver != self.expected_version:
            raise ValueError(
                f"Dataset version mismatch: expected {self.expected_version}, found {ver}"
            )
        return meta

    def load_raw_splits(self) -> Dict[str, pd.DataFrame]:
        """Load the 4 Parquet split DataFrames from disk."""
        splits = {}
        for split_name in ["train", "validation", "test", "cross_location_test"]:
            p = self.dataset_dir / f"{split_name}.parquet"
            if not p.is_file():
                raise FileNotFoundError(f"Required split file missing: {p}")
            splits[split_name] = pd.read_parquet(p)
        return splits

    def audit_ml_leakage(self, splits: Dict[str, pd.DataFrame]) -> None:
        """Audit features and splits for ML leakage before training."""
        train_df = splits["train"]
        val_df = splits["validation"]
        test_df = splits["test"]
        cross_df = splits["cross_location_test"]

        # 1. Target and simulator state must not be in feature columns
        for name, df in splits.items():
            feature_cols = [c for c in df.columns if c not in IDENTIFIER_COLUMNS and c != self.target_name]
            # No forbidden state
            for col in feature_cols:
                if col in FORBIDDEN_SIMULATOR_STATE:
                    raise ValueError(f"Simulator-state leakage in {name}: '{col}' in features")
                if "future" in col.lower() or ("target" in col.lower() and col != self.target_name):
                    raise ValueError(f"Feature leakage in {name}: '{col}' contains future/target semantics")

        # 2. Strict sample_id separation (no row overlap)
        train_ids = set(train_df["sample_id"])
        val_ids = set(val_df["sample_id"])
        test_ids = set(test_df["sample_id"])
        cross_ids = set(cross_df["sample_id"])

        if not train_ids.isdisjoint(val_ids):
            raise ValueError("Row overlap detected between train and validation!")
        if not train_ids.isdisjoint(test_ids):
            raise ValueError("Row overlap detected between train and test!")
        if not train_ids.isdisjoint(cross_ids):
            raise ValueError("Row overlap detected between train and cross_location_test!")

    def extract_features_and_targets(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
        """Separate DataFrame into (X_features, y_target, id_metadata).

        Returns
        -------
        X : pd.DataFrame
            Operational feature columns only.
        y : pd.Series
            Target column series.
        identifiers : pd.DataFrame
            Identification columns (sample_id, timestamp, region_id, location_id).
        """
        # Ensure target is present
        if self.target_name not in df.columns:
            raise KeyError(f"Target column '{self.target_name}' not found in DataFrame")

        # Verify operational features
        missing_features = [f for f in OPERATIONAL_FEATURES if f not in df.columns]
        if missing_features:
            raise KeyError(f"Missing required operational features: {missing_features}")

        X = df[OPERATIONAL_FEATURES].copy()
        y = df[self.target_name].copy()
        identifiers = df[IDENTIFIER_COLUMNS].copy()

        # Sanity assertion: target MUST NOT be in X
        assert self.target_name not in X.columns

        return X, y, identifiers

    def load_prepared_dataset(
        self,
    ) -> Dict[str, Dict[str, Union[pd.DataFrame, pd.Series]]]:
        """Load and prepare all splits with strict leakage validation."""
        raw_splits = self.load_raw_splits()
        self.audit_ml_leakage(raw_splits)

        prepared = {}
        for split_name, df in raw_splits.items():
            X, y, id_df = self.extract_features_and_targets(df)
            prepared[split_name] = {
                "X": X,
                "y": y,
                "identifiers": id_df,
            }
        return prepared


__all__ = [
    "OPERATIONAL_FEATURES",
    "IDENTIFIER_COLUMNS",
    "BenchmarkDataLoader",
]
