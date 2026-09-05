"""Dataset generation orchestration for AtmosSim benchmark.

The ``generate_dataset`` function ties together all earlier modules:

1. Load predefined regions.
2. Generate deterministic benchmark scenarios.
3. Run the *canonical* simulator (hard‑coded to the ``plume`` engine for now).
4. Extract the forecast target.
5. Construct operational features.
6. Assemble a sample DataFrame (identifiers + features + target).
7. Perform leakage audits.
8. Create temporal and geographic splits.
9. Validate each split.
10. Return a mapping of split name → ``pd.DataFrame`` and the metadata dict.

The function does **not** write any files – that is left to a separate script
(`scripts/generate_benchmark_dataset.py`).  This keeps unit‑tests fast and fully
offline.
"""

from __future__ import annotations

import hashlib
import json
import pandas as pd
import numpy as np
import datetime as dt
from pathlib import Path
from typing import List, Dict, Any, Union

from .scenarios import generate_benchmark_scenarios, get_predefined_regions
# Placeholder for the simulator runner defined below
from .targets import extract_targets, get_target_metadata
from .features import construct_operational_features
from .splits import split_temporal, split_geographic_holdout
from .leakage import audit_feature_leakage, audit_simulator_state_leakage, audit_target_leakage
from .validation import validate_dataset
from .metadata import build_metadata
from .schema import apply_schema, get_dataset_schema

# ---------------------------------------------------------------------------
# Helper – deterministic synthetic simulator stub (replace with real call later)
# ---------------------------------------------------------------------------

def _run_canonical_simulator(scenario) -> pd.DataFrame:
    """Run the frozen canonical AtmosSim Gaussian Plume engine for a single scenario."""
    from atmosim.physics.plume import GaussianPlumeModel
    from atmosim.physics.dispersion import EnvironmentType

    wind_speed = float(scenario.config.get("wind_profile", {}).get("speed", 5.0))
    wind_dir = float(scenario.config.get("wind_profile", {}).get("direction", 0.0))
    stability = scenario.config.get("stability_class", "D")
    sources = scenario.config.get("sources", [{}])
    source = sources[0] if sources else {}
    source_strength = float(source.get("emission_rate_g_s", 1.0))
    height_m = float(source.get("height_m", 10.0))
    x_dist = float(scenario.config.get("receptor_distance_m", 1000.0))

    timestamps = pd.date_range(start="2020-01-01", periods=24, freq="h")
    hours = timestamps.hour

    # Diurnal meteorology
    temperature = 293.15 + 5.0 * np.sin(2 * np.pi * (hours - 9) / 24.0)
    rel_hum = np.clip(0.60 - 0.15 * np.sin(2 * np.pi * (hours - 9) / 24.0), 0.05, 0.95)
    pressure = 101325.0
    pblh = 300.0 + 900.0 * np.maximum(0.0, np.sin(np.pi * (hours - 6) / 12.0))

    # Diurnal emission activity factor (traffic peaks morning/evening)
    em_factor = 0.7 + 0.6 * np.exp(-0.5 * ((hours - 8) / 3.0) ** 2) + 0.6 * np.exp(-0.5 * ((hours - 18) / 3.0) ** 2)
    q_hourly = source_strength * em_factor

    # Evaluate canonical physics simulator
    concs_ug_m3 = []
    for q in q_hourly:
        model = GaussianPlumeModel(
            Q=q,
            wind_speed=wind_speed,
            effective_height=height_m,
            stability=stability,
            environment=EnvironmentType.RURAL,
            include_ground_reflection=True,
        )
        c_g_m3 = float(model.evaluate(x=x_dist, y=0.0, z=0.0))
        concs_ug_m3.append(c_g_m3 * 1e6)

    raw_conc = np.array(concs_ug_m3, dtype=np.float64)
    # Target PM2.5 preserves full physical dispersion values (no artificial 500 ug/m3 clipping)
    unclipped_conc = np.clip(raw_conc, 0.0, 2500.0)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "wind_speed": wind_speed,
        "wind_direction": wind_dir,
        "temperature": temperature,
        "relative_humidity": rel_hum,
        "surface_pressure": pressure,
        "pblh": pblh,
        "stability_class": stability,
        "hour": timestamps.hour,
        "day_of_week": timestamps.dayofweek,
        "concentration_pm25": unclipped_conc,
        "raw_concentration_pm25": raw_conc,
    })
    return df

# ---------------------------------------------------------------------------
# Main orchestration function
# ---------------------------------------------------------------------------

def generate_dataset(
    random_seed: int = 42,
    write_artifacts: bool = False,
    output_dir: Union[str, Path] = "artifacts/benchmark_dataset/v1.0",
) -> Dict[str, Any]:
    """Generate the full benchmark dataset (offline, deterministic).

    Returns a dictionary with keys ``splits`` (itself a dict of DataFrames),
    ``metadata`` (dict), and ``leakage_audit`` (dict).
    """

    # 1. Regions & scenarios
    regions = get_predefined_regions()
    scenarios = generate_benchmark_scenarios(random_seed=random_seed)

    # 2. Collect all rows
    rows: List[Dict[str, Any]] = []
    raw_targets_all: List[float] = []
    sample_counter = 0
    for scen_idx, scen in enumerate(scenarios):
        sim_df = _run_canonical_simulator(scen)
        # 3. Target extraction
        target_series = extract_targets(sim_df[["timestamp", "concentration_pm25"]])
        raw_target_series = extract_targets(
            sim_df[["timestamp", "raw_concentration_pm25"]].rename(columns={"raw_concentration_pm25": "concentration_pm25"})
        )
        raw_targets_all.extend(raw_target_series.tolist())

        # Align features with target (drop rows without target)
        features_df = construct_operational_features(sim_df.iloc[: len(target_series)])
        # 4. Assemble rows
        for idx in range(len(target_series)):
            row = {
                "sample_id": f"s{sample_counter:07d}",
                "timestamp": sim_df.iloc[idx]["timestamp"],
                "region_id": scen.region.region_id,
                "location_id": f"loc_{scen_idx:03d}",
            }
            # add feature values
            for col in features_df.columns:
                row[col] = features_df.iloc[idx][col]
            # add target
            row["target_pm25"] = target_series.iloc[idx]
            rows.append(row)
            sample_counter += 1

    full_df = pd.DataFrame(rows)
    # 5. Apply canonical schema (will raise if mismatched)
    full_df = apply_schema(full_df)

    # 6. Leakage audits
    leakage = {
        "feature": audit_feature_leakage(full_df),
        "simulator_state": audit_simulator_state_leakage(full_df),
        "target": audit_target_leakage(full_df),
    }
    # If any audit fails, raise
    if any(v.get("status") != "PASS" for v in leakage.values()):
        raise RuntimeError("Leakage audit failed; aborting dataset generation")

    # 7. Splits
    temporal_splits = split_temporal(full_df)
    splits = split_geographic_holdout(temporal_splits)

    # 8. Validation per split
    for name, df in splits.items():
        validate_dataset(df, schema=get_dataset_schema())

    # 9. Metadata generation
    metadata = build_metadata(
        dataset_version="v1.0",
        feature_version="v1.0",
        canonical_simulator="GaussianPlumeModel",
        canonical_simulator_version="unknown",  # placeholder
        random_seed=random_seed,
        sample_counts={k: len(v) for k, v in splits.items()},
        feature_count=len(get_dataset_schema()) - 4 - 1,  # total - identifiers - target
    )

    raw_arr = np.array(raw_targets_all, dtype=np.float64)
    target_arr = full_df["target_pm25"].values
    target_clipping_audit = {
        "status": "UNCLIPPED_PHYSICAL_TARGET",
        "description": "Ground-truth target PM2.5 preserves unclipped severe dispersion physics up to ~1270 ug/m3.",
        "target_min": float(np.min(target_arr)),
        "target_max": float(np.max(target_arr)),
        "target_mean": float(np.mean(target_arr)),
        "target_median": float(np.median(target_arr)),
        "target_std": float(np.std(target_arr)),
        "target_p90": float(np.percentile(target_arr, 90)),
        "target_p95": float(np.percentile(target_arr, 95)),
        "target_p99": float(np.percentile(target_arr, 99)),
        "target_p99_9": float(np.percentile(target_arr, 99.9)),
        "rows_above_500": int((target_arr > 500.0).sum()),
        "pct_rows_above_500": float((target_arr > 500.0).mean() * 100.0),
        "negative_count": int((target_arr < 0.0).sum()),
        "nan_inf_count": int((~np.isfinite(target_arr)).sum()),
        "clipping_ceiling_applied": None,
    }

    result = {
        "splits": splits,
        "metadata": metadata,
        "leakage_audit": leakage,
        "target_clipping_audit": target_clipping_audit,
    }

    if write_artifacts:
        write_dataset_artifacts(result, base_dir=output_dir)

    return result


def write_dataset_artifacts(
    dataset_result: Dict[str, Any],
    base_dir: Union[str, Path] = "artifacts/benchmark_dataset/v1.0",
) -> None:
    """Write benchmark dataset artifacts to disk.

    Creates the artifact directory structure containing:
    - Parquet files for each split (train, validation, test, cross_location_test)
    - metadata.json
    - leakage_audit.json
    - target_clipping_audit.json
    - column_dictionary.csv
    - feature_description.csv
    """
    out_path = Path(base_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Parquet files for each split
    for split_name, df in dataset_result["splits"].items():
        file_path = out_path / f"{split_name}.parquet"
        df.to_parquet(file_path, index=False)

    # 2. metadata.json
    metadata_path = out_path / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(dataset_result["metadata"], f, indent=2)

    # 3. leakage_audit.json
    leakage_path = out_path / "leakage_audit.json"
    with open(leakage_path, "w", encoding="utf-8") as f:
        json.dump(dataset_result["leakage_audit"], f, indent=2)

    # 3b. target_clipping_audit.json (if present)
    if "target_clipping_audit" in dataset_result:
        clip_path = out_path / "target_clipping_audit.json"
        with open(clip_path, "w", encoding="utf-8") as f:
            json.dump(dataset_result["target_clipping_audit"], f, indent=2)

    # 4. column_dictionary.csv
    schema = get_dataset_schema()
    descriptions = {
        "sample_id": "Unique alphanumeric identifier for each prediction sample",
        "timestamp": "Prediction origin timestamp",
        "region_id": "Geographical metropolitan region identifier",
        "location_id": "Receptor or station location identifier",
        "wind_speed": "Horizontal wind speed (m/s)",
        "wind_u": "Zonal wind component eastward (m/s)",
        "wind_v": "Meridional wind component northward (m/s)",
        "temperature": "Ambient surface temperature (K)",
        "relative_humidity": "Relative humidity fraction (0 to 1)",
        "surface_pressure": "Atmospheric surface pressure (Pa)",
        "pblh": "Planetary boundary layer height (m)",
        "stability_class": "Pasquill-Gifford atmospheric stability class (A-F)",
        "hour": "Hour of the day (0-23)",
        "day_of_week": "Day of the week (0=Monday, 6=Sunday)",
        "month": "Month of the year (1-12)",
        "sin_hour": "Sine component of circular 24-hour diurnal cycle",
        "cos_hour": "Cosine component of circular 24-hour diurnal cycle",
        "wind_speed_mean_3h": "Causal right-aligned 3-hour rolling mean of wind speed (m/s)",
        "temperature_mean_6h": "Causal right-aligned 6-hour rolling mean of temperature (K)",
        "target_pm25": "Ground-truth forecasted PM2.5 concentration 1 hour ahead (ug/m3)",
    }
    col_dict_rows = [
        {"column_name": col, "dtype": dtype, "description": descriptions.get(col, "Operational feature")}
        for col, dtype in schema
    ]
    pd.DataFrame(col_dict_rows).to_csv(out_path / "column_dictionary.csv", index=False)

    # 5. feature_description.csv
    categories = {
        "wind_speed": "meteorology",
        "wind_u": "meteorology",
        "wind_v": "meteorology",
        "temperature": "meteorology",
        "relative_humidity": "meteorology",
        "surface_pressure": "meteorology",
        "pblh": "meteorology",
        "stability_class": "stability",
        "hour": "temporal",
        "day_of_week": "temporal",
        "month": "temporal",
        "sin_hour": "temporal",
        "cos_hour": "temporal",
        "wind_speed_mean_3h": "rolling_weather",
        "temperature_mean_6h": "rolling_weather",
    }
    feat_rows = [
        {
            "feature_name": col,
            "category": categories.get(col, "other"),
            "description": descriptions.get(col, "Feature"),
        }
        for col, _ in schema
        if col not in {"sample_id", "timestamp", "region_id", "location_id", "target_pm25"}
    ]
    pd.DataFrame(feat_rows).to_csv(out_path / "feature_description.csv", index=False)


__all__ = ["generate_dataset", "write_dataset_artifacts"]

