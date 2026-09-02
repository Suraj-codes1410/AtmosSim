"""Target extraction utilities for the AtmosSim benchmark dataset.

The canonical simulator (frozen during Phase 4/5) returns a DataFrame with a
column named ``concentration_pm25`` (µg m⁻³) for each receptor location and a
timestamp. ``extract_targets`` isolates the target column, attaches the proper
metadata (pollutant, unit, forecast horizon) and returns a ``pd.Series`` that can
be merged with the feature DataFrame.

The function performs **no** leakage: it never returns future values, and it does
not modify the feature set.
"""

from __future__ import annotations

import pandas as pd
from typing import Tuple, Dict, Any

# ---------------------------------------------------------------------------
# Configuration constants – in a real implementation these would be user‑configurable.
# ---------------------------------------------------------------------------

TARGET_POLLUTANT = "PM2.5"
TARGET_UNIT = "µg/m³"
FORECAST_HORIZON_HOURS = 1  # Predict 1 h ahead of the last available observation
TARGET_COLUMN_NAME = "target_pm25"


def extract_targets(sim_df: pd.DataFrame, forecast_horizon: int = FORECAST_HORIZON_HOURS) -> pd.Series:
    """Extract the forecast target from a simulator output DataFrame.

    Parameters
    ----------
    sim_df : pd.DataFrame
        Simulator output containing at least ``timestamp`` and ``concentration_pm25``.
    forecast_horizon : int
        Number of hours ahead to forecast. The function shifts the ``timestamp``
        forward by this amount and aligns the target values accordingly.

    Returns
    -------
    pd.Series
        Series indexed like ``sim_df`` (same length) where the value at row *i*
        is the concentration that will be observed ``forecast_horizon`` hours
        later. Rows where a future value is unavailable are dropped.
    """

    if "timestamp" not in sim_df.columns or "concentration_pm25" not in sim_df.columns:
        raise KeyError("Simulator output must contain 'timestamp' and 'concentration_pm25' columns")

    df = sim_df.copy()
    df = df.sort_values("timestamp")
    df["target_timestamp"] = df["timestamp"] + pd.Timedelta(hours=forecast_horizon)
    # Align future concentration as the target; use merge to ensure proper temporal join.
    future = df[["timestamp", "concentration_pm25"]].rename(columns={"timestamp": "target_timestamp", "concentration_pm25": TARGET_COLUMN_NAME})
    merged = pd.merge(df, future, on="target_timestamp", how="left")
    # Drop rows where future target is missing (i.e., last ``forecast_horizon`` rows)
    target_series = merged[TARGET_COLUMN_NAME].dropna().reset_index(drop=True)
    return target_series


def get_target_metadata() -> Dict[str, Any]:
    """Return a dictionary describing the target definition.

    This is used by the metadata generation step.
    """

    return {
        "target_name": TARGET_COLUMN_NAME,
        "pollutant": TARGET_POLLUTANT,
        "unit": TARGET_UNIT,
        "forecast_horizon_hours": FORECAST_HORIZON_HOURS,
    }

__all__ = ["extract_targets", "get_target_metadata"]
