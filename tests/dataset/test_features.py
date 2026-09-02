"""Unit tests for atmosim.dataset.features module."""

import numpy as np
import pandas as pd
import pytest

from atmosim.dataset.features import construct_operational_features


def test_wind_components_and_circular_time_features():
    df = pd.DataFrame({
        "timestamp": pd.date_range(start="2020-01-01", periods=3, freq="h"),
        "wind_speed": [5.0, 10.0, 0.0],
        "wind_direction": [0.0, 90.0, 180.0],
        "temperature": [298.15, 298.15, 298.15],
        "relative_humidity": [0.5, 0.5, 0.5],
        "surface_pressure": [101325.0, 101325.0, 101325.0],
        "pblh": [500.0, 500.0, 500.0],
        "stability_class": ["D", "D", "D"],
        "hour": [0, 12, 23],
        "day_of_week": [2, 2, 2],
    })

    feats = construct_operational_features(df)

    dir_rad = np.deg2rad(df["wind_direction"])
    expected_u = -df["wind_speed"] * np.sin(dir_rad)
    expected_v = -df["wind_speed"] * np.cos(dir_rad)
    pd.testing.assert_series_equal(feats["wind_u"], expected_u, check_names=False)
    pd.testing.assert_series_equal(feats["wind_v"], expected_v, check_names=False)

    hour = df["hour"]
    expected_sin = np.sin(2 * np.pi * hour / 24.0)
    expected_cos = np.cos(2 * np.pi * hour / 24.0)
    pd.testing.assert_series_equal(feats["sin_hour"], expected_sin, check_names=False)
    pd.testing.assert_series_equal(feats["cos_hour"], expected_cos, check_names=False)


def test_causal_rolling_features():
    """Verify that rolling features are right-aligned (causal) and never look into the future."""
    speeds = [2.0, 4.0, 6.0, 8.0, 10.0]
    temps = [280.0, 282.0, 284.0, 286.0, 288.0]
    df = pd.DataFrame({
        "timestamp": pd.date_range(start="2020-01-01 00:00", periods=5, freq="h"),
        "wind_speed": speeds,
        "wind_direction": [0.0] * 5,
        "temperature": temps,
        "relative_humidity": [0.5] * 5,
        "surface_pressure": [101325.0] * 5,
        "pblh": [500.0] * 5,
        "stability_class": ["D"] * 5,
        "hour": list(range(5)),
        "day_of_week": [0] * 5,
    })

    feats = construct_operational_features(df)

    # 3-hour window mean at index 0 (1 observation: 2.0)
    assert feats["wind_speed_mean_3h"].iloc[0] == 2.0
    # At index 1 (2 observations: [2.0, 4.0] -> 3.0)
    assert feats["wind_speed_mean_3h"].iloc[1] == 3.0
    # At index 2 (3 observations: [2.0, 4.0, 6.0] -> 4.0)
    assert feats["wind_speed_mean_3h"].iloc[2] == 4.0
    # At index 3 (3 observations: [4.0, 6.0, 8.0] -> 6.0)
    assert feats["wind_speed_mean_3h"].iloc[3] == 6.0

    # Changing future row does NOT affect past rolling mean
    df_modified_future = df.copy()
    df_modified_future.loc[4, "wind_speed"] = 999.0
    feats_modified = construct_operational_features(df_modified_future)
    pd.testing.assert_series_equal(
        feats["wind_speed_mean_3h"].iloc[:4],
        feats_modified["wind_speed_mean_3h"].iloc[:4],
    )


def test_missing_required_column_raises():
    df = pd.DataFrame({
        "timestamp": pd.date_range(start="2020-01-01", periods=2, freq="h"),
        "wind_speed": [5.0, 10.0],
        # wind_direction missing
        "temperature": [298.15, 298.15],
        "relative_humidity": [0.5, 0.5],
        "surface_pressure": [101325.0, 101325.0],
        "pblh": [500.0, 500.0],
        "stability_class": ["D", "D"],
        "hour": [0, 1],
        "day_of_week": [0, 0],
    })
    with pytest.raises(KeyError, match="Required column 'wind_direction' missing"):
        construct_operational_features(df)
