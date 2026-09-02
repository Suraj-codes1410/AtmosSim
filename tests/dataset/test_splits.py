"""Unit tests for dataset splitting in atmosim.dataset.splits."""

import pandas as pd
import pytest

from atmosim.dataset.splits import split_temporal, split_geographic_holdout


def test_split_temporal_chronological_order_and_ratios():
    n_samples = 100
    timestamps = pd.date_range("2020-01-01", periods=n_samples, freq="h")
    df = pd.DataFrame({
        "sample_id": [f"s_{i}" for i in range(n_samples)],
        "timestamp": timestamps,
        "region_id": ["R01"] * n_samples,
        "wind_speed": [5.0] * n_samples,
    })

    splits = split_temporal(df)
    assert set(splits.keys()) == {"train", "validation", "test"}
    train, val, test = splits["train"], splits["validation"], splits["test"]

    # 70%, 15%, 15%
    assert len(train) == 70
    assert len(val) == 15
    assert len(test) == 15

    # Check temporal ordering: max(train) <= min(val) and max(val) <= min(test)
    assert train["timestamp"].max() <= val["timestamp"].min()
    assert val["timestamp"].max() <= test["timestamp"].min()


def test_split_geographic_holdout_isolation():
    # 5 different regions
    regions = ["R01", "R02", "R03", "R04", "R05"]
    rows = []
    for r in regions:
        for t in pd.date_range("2020-01-01", periods=20, freq="h"):
            rows.append({
                "sample_id": f"{r}_{t}",
                "timestamp": t,
                "region_id": r,
                "wind_speed": 5.0,
            })
    df = pd.DataFrame(rows)

    temporal_splits = split_temporal(df)
    geo_splits = split_geographic_holdout(temporal_splits, holdout_fraction=0.20)

    assert set(geo_splits.keys()) == {"train", "validation", "test", "cross_location_test"}

    train_regions = set(geo_splits["train"]["region_id"].unique())
    val_regions = set(geo_splits["validation"]["region_id"].unique())
    test_regions = set(geo_splits["test"]["region_id"].unique())
    cross_regions = set(geo_splits["cross_location_test"]["region_id"].unique())

    # Ensure cross_regions has at least 1 region
    assert len(cross_regions) >= 1
    # Check strict geographic isolation: cross_regions must NOT overlap with train, val, or test
    assert cross_regions.isdisjoint(train_regions)
    assert cross_regions.isdisjoint(val_regions)
    assert cross_regions.isdisjoint(test_regions)

    # Total samples preserved
    total_original = len(df)
    total_split = (
        len(geo_splits["train"])
        + len(geo_splits["validation"])
        + len(geo_splits["test"])
        + len(geo_splits["cross_location_test"])
    )
    assert total_original == total_split
