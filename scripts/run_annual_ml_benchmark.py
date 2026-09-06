#!/usr/bin/env python3
"""CLI script to run ML Baseline Benchmarks across Multi-City Annual Continuous Datasets."""

from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

# Add src to python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np
import pandas as pd
import sklearn
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
import lightgbm as lgb
import catboost as cb

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


class PersistenceAnnualBaseline:
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
        # Lagged target by 1 hour within city series
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
    parser = argparse.ArgumentParser(description="Run Multi-City Annual Continuous ML Benchmark.")
    parser.add_argument("--data-dir", type=str, default="artifacts/annual_dataset", help="Path to annual datasets")
    parser.add_argument("--out-dir", type=str, default="artifacts/annual_ml", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("==========================================================================")
    print("      AtmosSim: Multi-City Annual Continuous ML Baseline Benchmark        ")
    print("==========================================================================")

    # Load 4 city datasets
    cities = ["delhi", "mumbai", "pune", "bengaluru"]
    dfs = {}
    for c in cities:
        p = data_dir / f"{c}_2023_annual_continuous.parquet"
        if not p.exists():
            raise FileNotFoundError(f"Missing dataset: {p}")
        df_c = pd.read_parquet(p)
        dfs[c] = df_c
        print(f"Loaded {c.capitalize():10s}: {len(df_c)} hours (Mean PM2.5: {df_c[TARGET_COL].mean():6.2f} ug/m3, Max: {df_c[TARGET_COL].max():7.2f})")

    results = {
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "git_commit": get_git_commit(),
        },
        "features": ANNUAL_OPERATIONAL_FEATURES,
        "target": TARGET_COL,
        "city_specific_temporal_benchmark": {},
        "zero_shot_cross_city_transfer": {},
        "pooled_multi_city_benchmark": {},
    }

    # 1. City-Specific Temporal Evaluation (Train: Jan-Aug, Val: Sep-Oct, Test: Nov-Dec)
    print("\n--- 1. City-Specific Temporal Benchmark (Train: Jan-Aug, Test: Nov-Dec) ---")
    for city_name, df_city in dfs.items():
        train_mask = df_city["month"] <= 8
        val_mask = (df_city["month"] >= 9) & (df_city["month"] <= 10)
        test_mask = df_city["month"] >= 11

        df_train = df_city[train_mask].copy()
        df_val = df_city[val_mask].copy()
        df_test = df_city[test_mask].copy()

        X_train_raw = df_train[ANNUAL_OPERATIONAL_FEATURES]
        y_train = df_train[TARGET_COL].values
        X_val_raw = df_val[ANNUAL_OPERATIONAL_FEATURES]
        y_val = df_val[TARGET_COL].values
        X_test_raw = df_test[ANNUAL_OPERATIONAL_FEATURES]
        y_test = df_test[TARGET_COL].values

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train_raw)
        X_val_scaled = scaler.transform(X_val_raw)
        X_test_scaled = scaler.transform(X_test_raw)

        models = {
            "persistence": PersistenceAnnualBaseline(),
            "linear": LinearRegression(),
            "ridge": Ridge(alpha=1.0, random_state=args.seed),
            "random_forest": RandomForestRegressor(n_estimators=100, max_depth=12, random_state=args.seed, n_jobs=-1),
            "xgboost": xgb.XGBRegressor(n_estimators=100, learning_rate=0.05, max_depth=6, random_state=args.seed, n_jobs=-1),
            "lightgbm": lgb.LGBMRegressor(n_estimators=100, learning_rate=0.05, num_leaves=31, random_state=args.seed, n_jobs=-1, verbose=-1),
            "catboost": cb.CatBoostRegressor(iterations=100, learning_rate=0.05, depth=6, random_seed=args.seed, verbose=0),
        }

        city_res = {}
        for m_name, model in models.items():
            is_linear = m_name in ["linear", "ridge"]
            is_persist = m_name == "persistence"

            if is_persist:
                model.fit(X_train_raw, y_train)
                pred_test = model.predict(df_test)
            elif is_linear:
                model.fit(X_train_scaled, y_train)
                pred_test = model.predict(X_test_scaled)
            else:
                model.fit(X_train_raw, y_train)
                pred_test = model.predict(X_test_raw)

            m_test = compute_all_metrics(y_test, pred_test)
            city_res[m_name] = m_test

        results["city_specific_temporal_benchmark"][city_name] = city_res
        rf_m = city_res["random_forest"]
        cb_m = city_res["catboost"]
        print(f"[{city_name.upper():10s}] RF Test MAE: {rf_m['mae']:6.2f}, RMSE: {rf_m['rmse']:6.2f}, R2: {rf_m['r2']:6.3f} | CatBoost Test MAE: {cb_m['mae']:6.2f}, R2: {cb_m['r2']:6.3f}")

    # 2. Pooled Multi-City Benchmark (All 4 cities with one-hot encoding)
    print("\n--- 2. Pooled Multi-City Benchmark (All 4 Cities Jointly) ---")
    pooled_df = pd.concat([dfs[c] for c in cities], ignore_index=True)
    pooled_df = pd.get_dummies(pooled_df, columns=["city"], drop_first=False)
    city_dummy_cols = [c for c in pooled_df.columns if c.startswith("city_")]
    pooled_features = ANNUAL_OPERATIONAL_FEATURES + city_dummy_cols

    train_mask = pooled_df["month"] <= 8
    val_mask = (pooled_df["month"] >= 9) & (pooled_df["month"] <= 10)
    test_mask = pooled_df["month"] >= 11

    df_train = pooled_df[train_mask].copy()
    df_val = pooled_df[val_mask].copy()
    df_test = pooled_df[test_mask].copy()

    X_train_raw = df_train[pooled_features]
    y_train = df_train[TARGET_COL].values
    X_test_raw = df_test[pooled_features]
    y_test = df_test[TARGET_COL].values

    models = {
        "persistence": PersistenceAnnualBaseline(),
        "random_forest": RandomForestRegressor(n_estimators=100, max_depth=12, random_state=args.seed, n_jobs=-1),
        "xgboost": xgb.XGBRegressor(n_estimators=100, learning_rate=0.05, max_depth=6, random_state=args.seed, n_jobs=-1),
        "lightgbm": lgb.LGBMRegressor(n_estimators=100, learning_rate=0.05, num_leaves=31, random_state=args.seed, n_jobs=-1, verbose=-1),
        "catboost": cb.CatBoostRegressor(iterations=100, learning_rate=0.05, depth=6, random_seed=args.seed, verbose=0),
    }

    for m_name, model in models.items():
        is_persist = m_name == "persistence"
        if is_persist:
            model.fit(X_train_raw, y_train)
            pred_test = model.predict(df_test)
        else:
            model.fit(X_train_raw, y_train)
            pred_test = model.predict(X_test_raw)

        m_test = compute_all_metrics(y_test, pred_test)
        results["pooled_multi_city_benchmark"][m_name] = m_test
        print(f"[POOLED - {m_name.upper():14s}] Test MAE: {m_test['mae']:6.2f}, RMSE: {m_test['rmse']:6.2f}, R2: {m_test['r2']:6.3f}")

    # Save metrics
    out_file = out_dir / "annual_ml_benchmark_metrics.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nSaved benchmark metrics to {out_file}")


if __name__ == "__main__":
    main()
