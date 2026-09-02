"""Leakage audit utilities for the AtmosSim benchmark dataset.

The three public functions each receive the full dataset DataFrame (including
identifiers, features, and target) and return a dictionary with a ``status``
field (``PASS`` or ``FAIL``) and a list of offending column names.

* ``audit_feature_leakage`` – checks that no feature column contains future
  information. In this scaffold we simply verify that no column name contains the
  word ``future`` or ``target``.
* ``audit_simulator_state_leakage`` – ensures that simulator‑internal state
  columns are absent. The list of forbidden columns is defined in
  ``_SIMULATOR_STATE_COLUMNS``.
* ``audit_target_leakage`` – makes sure the target column does not appear among
  the feature columns.

If any violation is detected, the function records the offending column names
and sets ``status`` to ``FAIL``.  The caller is expected to abort dataset
generation when any audit fails.
"""

from __future__ import annotations

import pandas as pd
from typing import List, Dict

# ---------------------------------------------------------------------------
# Known simulator‑state columns (these would exist in a full simulation output)
# ---------------------------------------------------------------------------
_SIMULATOR_STATE_COLUMNS: List[str] = [
    "puff_x",
    "puff_y",
    "puff_z",
    "puff_mass",
    "puff_age",
    "sigma_x",
    "sigma_y",
    "sigma_z",
    "concentration_field",
    "transported_mass",
    "trajectory_state",
    "source_transport_distance",
]


def _detect_future_columns(df: pd.DataFrame, target_column: str = "target_pm25") -> List[str]:
    """Return column names that hint at future information in features.

    A heuristic: any non-target column containing the substrings ``future`` or ``target``
    (case‑insensitive) is considered a leakage candidate.
    """

    feature_cols = [c for c in df.columns if c != target_column]
    lowered = [c.lower() for c in feature_cols]
    bad = [c for c, l in zip(feature_cols, lowered) if "future" in l or "target" in l]
    return bad


def audit_feature_leakage(df: pd.DataFrame, target_column: str = "target_pm25") -> Dict[str, any]:
    """Audit feature columns for future‑variable leakage.

    Returns a dict ``{"status": "PASS"|"FAIL", "offending_columns": [...]}``.
    """

    offending = _detect_future_columns(df, target_column=target_column)
    status = "PASS" if not offending else "FAIL"
    return {"status": status, "offending_columns": offending}


def audit_simulator_state_leakage(df: pd.DataFrame) -> Dict[str, any]:
    """Audit that no simulator‑internal state columns are present.
    """

    present = [c for c in _SIMULATOR_STATE_COLUMNS if c in df.columns]
    status = "PASS" if not present else "FAIL"
    return {"status": status, "offending_columns": present}


def audit_target_leakage(df: pd.DataFrame, target_column: str = "target_pm25") -> Dict[str, any]:
    """Ensure the target column or target information does not appear among the feature columns.
    """

    identifier_cols = {"sample_id", "timestamp", "region_id", "location_id"}
    feature_cols = [c for c in df.columns if c not in identifier_cols and c != target_column]

    offending = []
    for col in feature_cols:
        if col.lower() == target_column.lower() or "target" in col.lower() or col == "concentration_pm25":
            offending.append(col)

    if offending:
        return {"status": "FAIL", "offending_columns": offending}
    return {"status": "PASS", "offending_columns": []}

__all__ = [
    "audit_feature_leakage",
    "audit_simulator_state_leakage",
    "audit_target_leakage",
]
