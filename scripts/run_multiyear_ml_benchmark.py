#!/usr/bin/env python3
"""
Multi-Year Multi-City ML Baseline Benchmark for AtmosSim.

Trains baseline models (Persistence, Ridge, Random Forest, XGBoost, LightGBM, CatBoost)
on 2018-2022 (5 years, 175k rows), validates on 2023 (35k rows), and tests on out-of-sample
2024 holdout (35k rows) across all 4 validated Indian megacities.
"""

from __future__ import annotations
import argparse
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
import lightgbm as lgb
import catboost as cb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from atmosim.ml.metrics import compute_all_metrics

ANNUAL_OPERATIONAL_FEATURES = [
    "wind_speed_mps",
    "wind_u_mps",
    "wind_v_mps",
    "temperature_c",
    "relative_humidity_pct",
    "surface_pressure_hpa",
    "boundary_layer_height_m",
    "direct_normal_irradiance_w_m2",
    "cloud_cover_pct",
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
    "sin_hour",
    "cos_hour",
    "sin_month",
    "cos_month",
    "cams_regional_pm25",
]
TARGET_COL = "target_pm25"


class PersistenceMultiYearBaseline:
    def __init__(self):
        self.name = "persistence"
        self.last_val = 0.0
        self.fit_time_seconds = 0.0
        self.predict_time_seconds = 0.0

    def fit(self, X: pd.DataFrame, y: np.ndarray):
        t0 = time.perf_counter()
        self.last_val = float(np.mean(y))
        self.fit_time_seconds = time.perf_counter() - t0

    def predict(self, df_full: pd.DataFrame) -> np.ndarray:
        t0 = time.perf_counter()
        if TARGET_COL in df_full.columns:
            preds = df_full[TARGET_COL].shift(1).bfill().values
        else:
            preds = np.full(len(df_full), self.last_val)
        self.predict_time_seconds = time.perf_counter() - t0
        return preds


def get_git_commit() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "unknown"


def main():
    parser = argparse.ArgumentParser(description="Multi-Year ML Benchmark.")
    parser.add_argument(
        "--dataset-path",
        type=str,
        default="artifacts/multiyear_dataset/multicity_2018_2024_continuous_master.parquet",
        help="Path to master parquet dataset",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="artifacts/multiyear_ml",
        help="Directory to save ML metrics",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("================================================================================")
    print("      AtmosSim: Multi-Year Multi-City Continuous ML Benchmark (2018-2024)       ")
    print("================================================================================")
    print(f"Loading master dataset: {args.dataset_path}")
    df = pd.read_parquet(args.dataset_path)
    df["year"] = pd.to_datetime(df["timestamp"]).dt.year
    print(f"Loaded {len(df):,} total hourly records across {df['city'].nunique()} cities ({', '.join(df['city'].unique())})")

    # One-hot encode city
    df_encoded = pd.get_dummies(df, columns=["city"], drop_first=False)
    city_dummy_cols = [c for c in df_encoded.columns if c.startswith("city_")]
    feature_cols = ANNUAL_OPERATIONAL_FEATURES + city_dummy_cols

    # Temporal multi-year split:
    # Train: 2018-2022 (5 years)
    # Val:   2023 (1 year)
    # Test:  2024 (1 year out-of-sample holdout)
    train_mask = df_encoded["year"] <= 2022
    val_mask = df_encoded["year"] == 2023
    test_mask = df_encoded["year"] == 2024

    df_train = df_encoded[train_mask].copy()
    df_val = df_encoded[val_mask].copy()
    df_test = df_encoded[test_mask].copy()

    print(f"\nMulti-Year Splits:")
    print(f"  - Train (2018-2022): {len(df_train):,} rows")
    print(f"  - Val   (2023):      {len(df_val):,} rows")
    print(f"  - Test  (2024):      {len(df_test):,} rows (Strict Out-of-Sample Calendar Year Holdout)")

    X_train = df_train[feature_cols]
    y_train = df_train[TARGET_COL].values

    X_val = df_val[feature_cols]
    y_val = df_val[TARGET_COL].values

    X_test = df_test[feature_cols]
    y_test = df_test[TARGET_COL].values

    # Preprocessing
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    models = {
        "persistence": PersistenceMultiYearBaseline(),
        "ridge": Ridge(alpha=1.0, random_state=args.seed),
        "random_forest": RandomForestRegressor(n_estimators=100, max_depth=14, random_state=args.seed, n_jobs=-1),
        "xgboost": xgb.XGBRegressor(n_estimators=100, learning_rate=0.05, max_depth=6, random_state=args.seed, n_jobs=-1),
        "lightgbm": lgb.LGBMRegressor(n_estimators=100, learning_rate=0.05, num_leaves=31, random_state=args.seed, n_jobs=-1, verbose=-1),
        "catboost": cb.CatBoostRegressor(iterations=100, learning_rate=0.05, depth=6, random_seed=args.seed, verbose=0),
    }

    results = {
        "dataset_path": str(args.dataset_path),
        "total_records": len(df),
        "split_counts": {
            "train_2018_2022": len(df_train),
            "val_2023": len(df_val),
            "test_2024": len(df_test),
        },
        "features": feature_cols,
        "models": {},
        "per_city_test_2024": {},
        "runtimes": {},
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "git_commit": get_git_commit(),
        },
    }

    print("\n--- Training Models on Multi-Year Continuous Dataset (175k Samples) ---")
    for m_name, model in models.items():
        is_ridge = m_name == "ridge"
        is_persist = m_name == "persistence"

        t0 = time.perf_counter()
        if is_persist:
            model.fit(X_train, y_train)
        elif is_ridge:
            model.fit(X_train_scaled, y_train)
        else:
            model.fit(X_train, y_train)
        fit_time = time.perf_counter() - t0

        # Predictions
        t0 = time.perf_counter()
        if is_persist:
            pred_val = model.predict(df_val)
            pred_test = model.predict(df_test)
        elif is_ridge:
            pred_val = model.predict(X_val_scaled)
            pred_test = model.predict(X_test_scaled)
        else:
            pred_val = model.predict(X_val)
            pred_test = model.predict(X_test)
        pred_time = time.perf_counter() - t0

        m_val = compute_all_metrics(y_val, pred_val)
        m_test = compute_all_metrics(y_test, pred_test)

        results["runtimes"][m_name] = {"fit_time": fit_time, "predict_time": pred_time}
        results["models"][m_name] = {
            "validation_2023": m_val,
            "test_2024_holdout": m_test,
        }

        # Per-city test 2024 evaluation
        results["per_city_test_2024"][m_name] = {}
        for c in df["city"].unique():
            city_mask = df_test["city_" + c] == 1
            y_city_test = y_test[city_mask]
            pred_city_test = pred_test[city_mask]
            results["per_city_test_2024"][m_name][c] = compute_all_metrics(y_city_test, pred_city_test)

        print(f"[{m_name.upper():14s}] Fit: {fit_time:5.1f}s | "
              f"Val(2023) R2: {m_val['r2']:6.3f} | "
              f"Test(2024) MAE: {m_test['mae']:6.2f} ug/m3 | RMSE: {m_test['rmse']:6.2f} | R2: {m_test['r2']:6.3f}")

    out_file = out_dir / "multiyear_ml_benchmark_metrics.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved multi-year benchmark metrics to {out_file}")

    print("\n=========================================================================================================")
    print("                    MULTI-YEAR CONTINUOUS ML BENCHMARK RESULTS (2024 HOLDOUT)                            ")
    print("=========================================================================================================")
    print(f"{'Model':<15} | {'Test MAE':>9} | {'Test RMSE':>10} | {'Test R2':>8} | {'Delhi R2':>9} | {'Mumbai R2':>10} | {'Pune R2':>8} | {'Blr R2':>8}")
    print("---------------------------------------------------------------------------------------------------------")
    for m_name in models:
        tm = results["models"][m_name]["test_2024_holdout"]
        cm = results["per_city_test_2024"][m_name]
        print(f"{m_name:<15} | {tm['mae']:9.2f} | {tm['rmse']:10.2f} | {tm['r2']:8.3f} | "
              f"{cm['Delhi']['r2']:9.3f} | {cm['Mumbai']['r2']:10.3f} | {cm['Pune']['r2']:8.3f} | {cm['Bengaluru']['r2']:8.3f}")
    print("=========================================================================================================\n")


if __name__ == "__main__":
    main()
