"""Feature construction utilities for the AtmosSim benchmark dataset.

The functions operate on a *simulation output* DataFrame that already contains
meteorological variables (wind speed, wind direction, temperature, humidity,
pressure, PBLH, stability class) and on a ``BenchmarkScenario`` instance for
region metadata.

All features are *operational*: they use only information that would be
available at the prediction timestamp. Rolling features are implemented with
``window='Xh'`` windows that **end** at the current timestamp – no centered or
future windows are used.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import List, Dict

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _wind_components(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``wind_u`` and ``wind_v`` columns derived from speed/direction.

    The convention follows meteorological convention where wind direction is the
    direction **from** which the wind blows (degrees clockwise from north).
    ``u`` is positive eastward, ``v`` positive northward.
    """

    speed = df["wind_speed"].astype(float)
    direction_deg = df["wind_direction"].astype(float)
    # Convert to radians and compute components (note the sign reversal for meteorology)
    rad = np.deg2rad(direction_deg)
    df = df.copy()
    df["wind_u"] = -speed * np.sin(rad)
    df["wind_v"] = -speed * np.cos(rad)
    return df


def _circular_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add sin/cos encodings for hour and day‑of‑week.
    ``hour`` is assumed to be integer 0‑23, ``day_of_week`` 0‑6.
    """

    df = df.copy()
    df["sin_hour"] = np.sin(2 * np.pi * df["hour"] / 24.0)
    df["cos_hour"] = np.cos(2 * np.pi * df["hour"] / 24.0)
    df["sin_day_of_week"] = np.sin(2 * np.pi * df["day_of_week"] / 7.0)
    df["cos_day_of_week"] = np.cos(2 * np.pi * df["day_of_week"] / 7.0)
    return df


def _rolling_features(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
    """Create causal rolling weather features.

    The DataFrame is expected to be sorted by ``timestamp`` and indexed by it.
    Rolling windows are defined in hours (e.g. 3h, 6h). The windows are *right‑
    aligned* so that the last element of each window coincides with the current
    timestamp.
    """

    df = df.set_index(timestamp_col)
    # Ensure monotonic index for rolling
    df = df.sort_index()
    # Example rolling features – can be extended later
    df["wind_speed_mean_3h"] = df["wind_speed"].rolling("3h").mean()
    df["temperature_mean_6h"] = df["temperature"].rolling("6h").mean()
    df = df.reset_index()
    return df

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def construct_operational_features(sim_df: pd.DataFrame) -> pd.DataFrame:
    """Generate the full set of operational features.

    The function returns a new DataFrame containing **only** feature columns
    (no target, no simulator‑internal columns). The caller is responsible for
    merging these features with the target column later.
    """

    # Expected input columns (minimal set). Missing columns will raise KeyError –
    # this is intentional because the benchmark must be deterministic.
    required = [
        "wind_speed",
        "wind_direction",
        "temperature",
        "relative_humidity",
        "surface_pressure",
        "pblh",
        "stability_class",
        "hour",
        "day_of_week",
        "timestamp",
    ]
    for col in required:
        if col not in sim_df.columns:
            raise KeyError(f"Required column '{col}' missing from simulation output")

    df = sim_df.copy()
    if "month" not in df.columns and "timestamp" in df.columns:
        df["month"] = pd.to_datetime(df["timestamp"]).dt.month
    if "road_density_total" not in df.columns:
        df["road_density_total"] = 0.0
    if "source_density" not in df.columns:
        df["source_density"] = 0.0

    df = _wind_components(df)
    df = _circular_time_features(df)
    df = _rolling_features(df)

    # Keep only the columns defined in the schema's feature list (import to avoid circular dep)
    from .schema import _FEATURE_COLUMNS  # type: ignore

    feature_names = [name for name, _ in _FEATURE_COLUMNS]
    # Preserve any extra columns that may be added later by the user – they will be filtered out here.
    df_features = df[feature_names]
    return df_features

__all__ = ["construct_operational_features"]
