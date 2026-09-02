"""Unit tests for dataset validation in atmosim.dataset.validation."""

import numpy as np
import pandas as pd
import pytest

from atmosim.dataset.schema import get_dataset_schema
from atmosim.dataset.validation import validate_dataset


def _make_valid_sample_df(n: int = 5) -> pd.DataFrame:
    schema = get_dataset_schema()
    timestamps = pd.date_range("2020-01-01", periods=n, freq="h")
    data = {}
    for col, dtype in schema:
        if col == "sample_id":
            data[col] = [f"s{i:05d}" for i in range(n)]
        elif col == "timestamp":
            data[col] = timestamps
        elif col == "region_id":
            data[col] = ["R01"] * n
        elif col == "location_id":
            data[col] = [f"loc_{i}" for i in range(n)]
        elif col == "stability_class":
            data[col] = ["D"] * n
        elif col in {"hour", "day_of_week", "month"}:
            data[col] = [1] * n
        elif col in {"sin_hour", "cos_hour"}:
            data[col] = [0.5] * n
        elif col == "temperature":
            data[col] = [293.15] * n
        elif col == "surface_pressure":
            data[col] = [101325.0] * n
        elif col == "relative_humidity":
            data[col] = [0.5] * n
        elif col == "pblh":
            data[col] = [800.0] * n
        elif col == "target_pm25":
            data[col] = [15.0] * n
        else:
            data[col] = [5.0] * n

    df = pd.DataFrame(data)
    for col, dtype in schema:
        df[col] = df[col].astype(dtype)
    return df


def test_valid_dataset_passes():
    df = _make_valid_sample_df()
    # Should complete without error
    assert validate_dataset(df) is None


def test_duplicate_sample_id_raises():
    df = _make_valid_sample_df()
    df.loc[1, "sample_id"] = df.loc[0, "sample_id"]
    with pytest.raises(ValueError, match="Duplicate sample_id detected"):
        validate_dataset(df)


def test_null_sample_id_raises():
    df = _make_valid_sample_df()
    df.loc[0, "sample_id"] = None
    with pytest.raises(ValueError, match="Null sample_id detected"):
        validate_dataset(df)


def test_all_nan_feature_raises():
    df = _make_valid_sample_df()
    df["wind_speed"] = np.nan
    with pytest.raises(ValueError, match="contains only missing values"):
        validate_dataset(df)


def test_out_of_range_raises():
    df = _make_valid_sample_df()
    df.loc[0, "temperature"] = 9999.0  # Plausible range is 200..350 K
    with pytest.raises(ValueError, match="Columns out of plausible range"):
        validate_dataset(df)


def test_failed_leakage_audit_raises():
    df = _make_valid_sample_df()
    leakage = {
        "feature": {"status": "FAIL", "offending_columns": ["future_temp"]},
    }
    with pytest.raises(ValueError, match="Leakage audit 'feature' failed"):
        validate_dataset(df, leakage_audit=leakage)
