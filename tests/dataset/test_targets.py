"""Unit tests for target extraction in atmosim.dataset.targets."""

import pandas as pd
import pytest

from atmosim.dataset.targets import (
    extract_targets,
    get_target_metadata,
    TARGET_COLUMN_NAME,
    TARGET_POLLUTANT,
    TARGET_UNIT,
    FORECAST_HORIZON_HOURS,
)


def test_extract_targets_shift_and_alignment():
    timestamps = pd.date_range("2023-01-01 00:00", periods=5, freq="h")
    concs = [10.0, 15.0, 20.0, 25.0, 30.0]
    df = pd.DataFrame({
        "timestamp": timestamps,
        "concentration_pm25": concs,
    })

    # Default horizon is 1 hour
    targets = extract_targets(df, forecast_horizon=1)

    # With 5 hours and 1 hour ahead target, rows 0..3 have future targets:
    # row 0 (00:00) -> conc at 01:00 (15.0)
    # row 1 (01:00) -> conc at 02:00 (20.0)
    # row 2 (02:00) -> conc at 03:00 (25.0)
    # row 3 (03:00) -> conc at 04:00 (30.0)
    assert len(targets) == 4
    expected = [15.0, 20.0, 25.0, 30.0]
    assert list(targets) == expected


def test_extract_targets_multi_hour_horizon():
    timestamps = pd.date_range("2023-01-01 00:00", periods=6, freq="h")
    concs = [10.0, 12.0, 14.0, 16.0, 18.0, 20.0]
    df = pd.DataFrame({
        "timestamp": timestamps,
        "concentration_pm25": concs,
    })

    targets = extract_targets(df, forecast_horizon=2)
    # rows 0..3 have 2-hour ahead future targets
    assert len(targets) == 4
    expected = [14.0, 16.0, 18.0, 20.0]
    assert list(targets) == expected


def test_extract_targets_missing_columns_raises():
    df = pd.DataFrame({"timestamp": pd.date_range("2023-01-01", periods=3, freq="h")})
    with pytest.raises(KeyError, match="must contain 'timestamp' and 'concentration_pm25'"):
        extract_targets(df)


def test_get_target_metadata():
    meta = get_target_metadata()
    assert meta["target_name"] == TARGET_COLUMN_NAME
    assert meta["pollutant"] == TARGET_POLLUTANT
    assert meta["unit"] == TARGET_UNIT
    assert meta["forecast_horizon_hours"] == FORECAST_HORIZON_HOURS
