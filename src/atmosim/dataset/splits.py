"""Dataset split utilities for the AtmosSim benchmark.

Two split stages are required:

* ``split_temporal`` – chronological 70 % train / 15 % validation / 15 % test.
* ``split_geographic_holdout`` – creates a cross‑location holdout that contains
  only regions not present in the temporal splits.

Both functions return dictionaries mapping split name → DataFrame. The input
DataFrame is assumed to already contain ``region_id`` and ``timestamp`` columns.
"""

from __future__ import annotations

import pandas as pd
from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# Temporal split (70/15/15) – deterministic based on ordering of timestamps.
# ---------------------------------------------------------------------------

def split_temporal(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Chronologically split ``df`` into train / validation / test by unique timestamps.

    The split percentages are fixed at 70% / 15% / 15% of unique timestamps
    to ensure zero temporal overlap across independent scenario time series.
    """

    df_sorted = df.sort_values("timestamp").reset_index(drop=True)
    unique_ts = sorted(df_sorted["timestamp"].unique())
    n_ts = len(unique_ts)
    train_end_idx = int(0.70 * n_ts)
    val_end_idx = train_end_idx + int(0.15 * n_ts)

    train_ts = set(unique_ts[:train_end_idx])
    val_ts = set(unique_ts[train_end_idx:val_end_idx])
    test_ts = set(unique_ts[val_end_idx:])

    train = df_sorted[df_sorted["timestamp"].isin(train_ts)].copy().reset_index(drop=True)
    validation = df_sorted[df_sorted["timestamp"].isin(val_ts)].copy().reset_index(drop=True)
    test = df_sorted[df_sorted["timestamp"].isin(test_ts)].copy().reset_index(drop=True)

    return {"train": train, "validation": validation, "test": test}

# ---------------------------------------------------------------------------
# Geographic holdout – moves *entire* regions to a separate split.
# ---------------------------------------------------------------------------

def split_geographic_holdout(
    splits: Dict[str, pd.DataFrame], holdout_fraction: float = 0.20
) -> Dict[str, pd.DataFrame]:
    """Create a cross‑location holdout split.

    Parameters
    ----------
    splits: dict
        Result of ``split_temporal`` containing ``train``, ``validation`` and
        ``test`` DataFrames.
    holdout_fraction: float
        Fraction of *distinct* regions to move to the holdout. Default 20 %.

    Returns
    -------
    dict
        Mapping with the original three splits (now possibly reduced) plus a
        ``cross_location_test`` DataFrame containing the removed regions.
    """

    # Gather all unique region IDs across the three temporal splits.
    all_regions = pd.concat([splits["train"], splits["validation"], splits["test"]])["region_id"].unique()
    n_holdout = max(1, int(len(all_regions) * holdout_fraction))
    # Deterministically pick the first ``n_holdout`` region IDs (sorted).
    holdout_regions = sorted(all_regions)[:n_holdout]

    cross_holdout_frames = []
    for name in ["train", "validation", "test"]:
        df = splits[name]
        holdout_part = df[df["region_id"].isin(holdout_regions)]
        cross_holdout_frames.append(holdout_part)
        splits[name] = df[~df["region_id"].isin(holdout_regions)].copy().reset_index(drop=True)

    cross_location_test = pd.concat(cross_holdout_frames, ignore_index=True)
    result = dict(splits)
    result["cross_location_test"] = cross_location_test
    return result

__all__ = ["split_temporal", "split_geographic_holdout"]
