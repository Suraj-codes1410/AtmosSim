"""Unit tests for ML dataset loader, schema validation, and leakage protection."""

import json
from pathlib import Path
import pandas as pd
import pytest

from atmosim.ml.splits import BenchmarkDataLoader, OPERATIONAL_FEATURES, IDENTIFIER_COLUMNS


@pytest.fixture
def dummy_release_dir(tmp_path):
    d = tmp_path / "v1.0"
    d.mkdir(parents=True)

    metadata = {
        "dataset_version": "v1.0",
        "feature_version": "v1.0",
        "target": "target_pm25",
        "sample_counts": {"train": 10, "validation": 5, "test": 5, "cross_location_test": 5},
    }
    with open(d / "metadata.json", "w") as f:
        json.dump(metadata, f)

    # Create dummy splits
    def make_df(sample_ids):
        data = {
            "sample_id": sample_ids,
            "timestamp": pd.date_range("2020-01-01", periods=len(sample_ids), freq="h"),
            "region_id": ["R001"] * len(sample_ids),
            "location_id": ["loc_0"] * len(sample_ids),
            "target_pm25": [25.0] * len(sample_ids),
        }
        for f in OPERATIONAL_FEATURES:
            data[f] = 1.0 if f != "stability_class" else "D"
        return pd.DataFrame(data)

    make_df([f"tr_{i}" for i in range(10)]).to_parquet(d / "train.parquet")
    make_df([f"val_{i}" for i in range(5)]).to_parquet(d / "validation.parquet")
    make_df([f"te_{i}" for i in range(5)]).to_parquet(d / "test.parquet")
    make_df([f"cr_{i}" for i in range(5)]).to_parquet(d / "cross_location_test.parquet")

    return d


def test_loader_valid_release(dummy_release_dir):
    loader = BenchmarkDataLoader(dummy_release_dir, expected_dataset_version="v1.0")
    prepared = loader.load_prepared_dataset()
    assert set(prepared.keys()) == {"train", "validation", "test", "cross_location_test"}

    train_data = prepared["train"]
    X = train_data["X"]
    y = train_data["y"]
    ids = train_data["identifiers"]

    # Target not in X
    assert "target_pm25" not in X.columns
    assert len(X.columns) == len(OPERATIONAL_FEATURES)
    assert set(ids.columns) == set(IDENTIFIER_COLUMNS)
    assert len(y) == 10


def test_loader_version_mismatch(dummy_release_dir):
    with pytest.raises(ValueError, match="version mismatch"):
        BenchmarkDataLoader(dummy_release_dir, expected_dataset_version="v2.0")


def test_loader_detects_row_overlap(dummy_release_dir):
    # Make train and test share a sample_id
    df_overlap = pd.read_parquet(dummy_release_dir / "test.parquet")
    df_overlap.loc[0, "sample_id"] = "tr_0"
    df_overlap.to_parquet(dummy_release_dir / "test.parquet")

    loader = BenchmarkDataLoader(dummy_release_dir, expected_dataset_version="v1.0")
    with pytest.raises(ValueError, match="Row overlap detected"):
        loader.load_prepared_dataset()


def test_loader_detects_simulator_state_leakage(dummy_release_dir):
    df_leak = pd.read_parquet(dummy_release_dir / "train.parquet")
    df_leak["puff_mass"] = 100.0
    df_leak.to_parquet(dummy_release_dir / "train.parquet")

    loader = BenchmarkDataLoader(dummy_release_dir, expected_dataset_version="v1.0")
    with pytest.raises(ValueError, match="Simulator-state leakage"):
        loader.load_prepared_dataset()
