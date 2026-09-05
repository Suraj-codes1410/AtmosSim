"""Dataset validation utilities for the AtmosSim benchmark.

The ``validate_dataset`` function runs a series of checks on a DataFrame:

* schema conformity (columns, order, dtypes)
* unique ``sample_id``
* no missing values in identifier columns
* reasonable value ranges for a subset of features (example thresholds)
* leakage audit status (expects the leakage audit dict to be passed in)

If any check fails, a ``ValueError`` is raised with a helpful message.
"""

from __future__ import annotations

import pandas as pd
from typing import List, Dict, Any

from .schema import apply_schema, get_dataset_schema

# ---------------------------------------------------------------------------
# Helper range checks – these thresholds are illustrative and can be adjusted
# ---------------------------------------------------------------------------
_FEATURE_RANGES: Dict[str, Tuple[float, float]] = {
    "wind_speed": (0.0, 50.0),  # m/s
    "temperature": (200.0, 350.0),  # K
    "relative_humidity": (0.0, 1.0),
    "surface_pressure": (80000.0, 110000.0),  # Pa
    "pblh": (0.0, 5000.0),
    "target_pm25": (0.0, 2500.0),  # µg/m³ (unclipped severe inversion physics)
}


def _check_ranges(df: pd.DataFrame) -> List[str]:
    """Return a list of feature names that violate their configured ranges."""

    violations = []
    for col, (low, high) in _FEATURE_RANGES.items():
        if col not in df.columns:
            continue
        if not ((df[col] >= low) & (df[col] <= high)).all():
            violations.append(col)
    return violations


def validate_dataset(
    df: pd.DataFrame,
    schema: List[Tuple[str, str]] = None,
    leakage_audit: Dict[str, Any] = None,
) -> None:
    """Validate a benchmark split.

    Parameters
    ----------
    df: pd.DataFrame
        The split to validate.
    schema: list of (name, dtype) tuples (optional)
        If omitted the default dataset schema is used.
    leakage_audit: dict (optional)
        Output of the leakage audit; if provided the function ensures all audits
        have ``status == 'PASS'``.
    """

    # 1. Schema & dtype enforcement
    if schema is None:
        schema = get_dataset_schema()
    df = apply_schema(df)  # will raise if mismatched

    # 2. Identifier uniqueness & non‑null
    if df["sample_id"].isnull().any():
        raise ValueError("Null sample_id detected")
    if df["sample_id"].duplicated().any():
        raise ValueError("Duplicate sample_id detected")

    # 3. Missingness in feature columns – allowed but reported (no error)
    # For strictness we fail if any feature column is entirely NaN.
    feature_cols = [c for c, _ in schema if c not in {"sample_id", "timestamp", "region_id", "location_id", "target_pm25"}]
    for col in feature_cols:
        if df[col].isna().all():
            raise ValueError(f"Feature column '{col}' contains only missing values")

    # 4. Value‑range sanity checks
    bad = _check_ranges(df)
    if bad:
        raise ValueError(f"Columns out of plausible range: {bad}")

    # 5. Leakage audit status (if supplied)
    if leakage_audit:
        for name, report in leakage_audit.items():
            if report.get("status") != "PASS":
                raise ValueError(f"Leakage audit '{name}' failed: {report.get('offending_columns')}")

    # If we reach this point the dataset passes all checks.
    return None

__all__ = ["validate_dataset"]
