"""Dataset schema definitions for the AtmosSim benchmark dataset.

The schema is expressed as an ordered list of column specifications. Each entry is a tuple
```
(name, pandas_dtype)
```
which can be used to construct a pandas DataFrame with a consistent ordering across all
splits. The helper ``apply_schema`` casts a DataFrame to the canonical schema and raises
if unexpected columns are present.
"""

from __future__ import annotations

import pandas as pd
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Canonical column ordering and dtype mapping
# ---------------------------------------------------------------------------

# Core identifiers – must appear first and never be missing
_CORE_COLUMNS: List[Tuple[str, str]] = [
    ("sample_id", "string"),
    ("timestamp", "datetime64[ns]"),
    ("region_id", "string"),
    ("location_id", "string"),
]

# Operational feature columns – these are illustrative but cover all required
# groups. The concrete feature generation code must respect these names.
_FEATURE_COLUMNS: List[Tuple[str, str]] = [
    # Meteorology
    ("wind_speed", "float64"),
    ("wind_u", "float64"),
    ("wind_v", "float64"),
    ("temperature", "float64"),
    ("relative_humidity", "float64"),
    ("surface_pressure", "float64"),
    ("pblh", "float64"),
    ("stability_class", "string"),
    # Temporal / calendar
    ("hour", "int8"),
    ("day_of_week", "int8"),
    ("month", "int8"),
    ("sin_hour", "float64"),
    ("cos_hour", "float64"),
    # Rolling weather
    ("wind_speed_mean_3h", "float64"),
    ("temperature_mean_6h", "float64"),
    # Geographic / road density (example placeholders)
    ("road_density_total", "float64"),
    ("source_density", "float64"),
]

# Target column – appended after features
_TARGET_COLUMN: List[Tuple[str, str]] = [("target_pm25", "float64")]

# Assemble the full schema in the required order
FULL_SCHEMA: List[Tuple[str, str]] = _CORE_COLUMNS + _FEATURE_COLUMNS + _TARGET_COLUMN


def get_dataset_schema() -> List[Tuple[str, str]]:
    """Return the canonical column ordering and pandas dtypes.

    The caller can use this list to create a ``pandas.DataFrame`` with the correct
    column order, e.g.:

    ```python
    schema = get_dataset_schema()
    df = pd.DataFrame(columns=[c for c, _ in schema])
    for col, dtype in schema:
        df[col] = df[col].astype(dtype)
    ```
    """

    return list(FULL_SCHEMA)


def apply_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Cast ``df`` to the canonical schema and verify column consistency.

    Parameters
    ----------
    df: pd.DataFrame – Input data that should already contain the required columns.

    Returns
    -------
    pd.DataFrame – DataFrame with columns ordered exactly as the schema and dtypes
    coerced. Raises ``ValueError`` if a required column is missing or if unexpected
    columns are present.
    """

    expected = [c for c, _ in FULL_SCHEMA]
    missing = set(expected) - set(df.columns)
    extra = set(df.columns) - set(expected)
    if missing:
        raise ValueError(f"Missing required dataset columns: {sorted(missing)}")
    if extra:
        raise ValueError(f"Unexpected columns in dataset: {sorted(extra)}")

    # Reorder and cast dtypes
    ordered = df[expected].copy()
    for col, dtype in FULL_SCHEMA:
        ordered[col] = ordered[col].astype(dtype)
    return ordered

__all__ = ["get_dataset_schema", "apply_schema", "FULL_SCHEMA"]
