#!/usr/bin/env python3
"""CLI orchestration script to execute the AtmosSim Phase 7 ML Baseline Benchmark."""

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
import xgboost as xgb
import lightgbm as lgb
import catboost as cb

from atmosim.ml.splits import BenchmarkDataLoader, OPERATIONAL_FEATURES
from atmosim.ml.preprocessing import MLDataPreprocessor
from atmosim.ml.baselines import (
    PersistenceBaseline,
    LinearRegressionBaseline,
    RidgeBaseline,
    RandomForestBaseline,
    XGBoostBaseline,
    LightGBMBaseline,
    CatBoostBaseline,
)
from atmosim.ml.evaluation import ModelEvaluator
from atmosim.ml.diagnostics import generate_all_diagnostics


def get_git_commit() -> str:
    """Retrieve current git commit hash safely."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def main():
    parser = argparse.ArgumentParser(description="Run AtmosSim Phase 7 ML Baseline Benchmark.")
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default="artifacts/benchmark_dataset/v1.0",
        help="Path to Phase 6 benchmark dataset release directory",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="artifacts/ml",
        help="Output directory for ML benchmark artifacts",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Global random seed for reproducibility",
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    diag_dir = out_dir / "diagnostics"

    print("================================================================")
    print("      AtmosSim Phase 7: Reproducible ML Baseline Benchmark      ")
    print("================================================================")
    print(f"Dataset directory: {dataset_path.resolve()}")
    print(f"Output directory:  {out_dir.resolve()}")
    print(f"Random seed:       {args.seed}")

    # 1. Load and validate dataset release
    loader = BenchmarkDataLoader(dataset_path, expected_dataset_version="v1.0")
    prepared = loader.load_prepared_dataset()
    meta = loader.metadata

    print("\n--- Dataset Contract Verified ---")
    print(f"Dataset Version:  {meta.get('dataset_version')}")
    print(f"Feature Version:  {meta.get('feature_version')}")
    print(f"Target Column:    {loader.target_name}")
    print(f"Canonical Model:  {meta.get('canonical_simulator')}")
    print("Sample counts:")
    for s_name, s_data in prepared.items():
        print(f"  - {s_name}: {len(s_data['y'])} rows, {s_data['X'].shape[1]} features")

    # 2. Setup Preprocessing (Fit strictly on train)
    print("\n--- Fitting Preprocessing Pipeline (Train Split Only) ---")
    X_train_raw = prepared["train"]["X"]
    y_train = prepared["train"]["y"].values
    timestamps_train = prepared["train"]["identifiers"]["timestamp"]

    preprocessor = MLDataPreprocessor()
    preprocessor.fit(X_train_raw)

    # Preprocessed matrices
    X_train_lin = preprocessor.transform_linear(X_train_raw)
    X_train_tree = preprocessor.transform_tree(X_train_raw)

    # Evaluator initialized with training target distribution
    evaluator = ModelEvaluator(y_train=y_train)
    print(f"Extreme target thresholds: P90={evaluator.extreme_thresholds['top_10_percent']:.2f}, "
          f"P95={evaluator.extreme_thresholds['top_5_percent']:.2f}, "
          f"P99={evaluator.extreme_thresholds['top_1_percent']:.2f} ug/m3")

    # 3. Instantiate Models
    models = {
        "persistence": PersistenceBaseline(),
        "linear": LinearRegressionBaseline(),
        "ridge": RidgeBaseline(alpha=1.0, random_state=args.seed),
        "random_forest": RandomForestBaseline(n_estimators=100, max_depth=12, random_state=args.seed),
        "xgboost": XGBoostBaseline(n_estimators=100, learning_rate=0.05, max_depth=6, random_state=args.seed),
        "lightgbm": LightGBMBaseline(n_estimators=100, learning_rate=0.05, num_leaves=31, random_state=args.seed),
        "catboost": CatBoostBaseline(iterations=100, learning_rate=0.05, depth=6, random_seed=args.seed),
    }

    # Transform all evaluation splits
    split_transformed = {}
    for s_name in ["validation", "test", "cross_location_test"]:
        X_raw = prepared[s_name]["X"]
        y_val = prepared[s_name]["y"].values
        ts = prepared[s_name]["identifiers"]["timestamp"]
        split_transformed[s_name] = {
            "linear": preprocessor.transform_linear(X_raw),
            "tree": preprocessor.transform_tree(X_raw),
            "y": y_val,
            "timestamps": ts,
        }

    # 4. Train and Evaluate Each Model
    benchmark_metrics = {
        "dataset_version": meta.get("dataset_version"),
        "feature_version": meta.get("feature_version"),
        "target": loader.target_name,
        "forecast_horizon": "1 hour",
        "models": {},
        "seasonal_results": {},
        "extreme_value_results": {},
        "temporal_generalization": {},
        "geographic_generalization": {},
        "runtimes": {},
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "package_versions": {
                "scikit-learn": sklearn.__version__,
                "xgboost": xgb.__version__,
                "lightgbm": lgb.__version__,
                "catboost": cb.__version__,
                "numpy": np.__version__,
                "pandas": pd.__version__,
            },
            "git_commit": get_git_commit(),
        },
    }

    all_predictions = {}

    print("\n--- Training and Evaluating Baseline Models ---")
    for model_key, model in models.items():
        is_linear_type = model_key in ["linear", "ridge"]
        is_persistence = model_key == "persistence"

        # Fit
        if is_persistence:
            model.fit(X_train_raw, y_train)
        elif is_linear_type:
            model.fit(X_train_lin, y_train)
        else:
            model.fit(X_train_tree, y_train)

        benchmark_metrics["runtimes"][model_key] = {
            "fit_time_seconds": float(model.fit_time_seconds),
            "predict_time_seconds": float(model.predict_time_seconds),
        }

        # Evaluate across splits
        benchmark_metrics["models"][model_key] = {}
        all_predictions[model_key] = {}
        benchmark_metrics["extreme_value_results"][model_key] = {}
        benchmark_metrics["seasonal_results"][model_key] = {}

        for s_name in ["validation", "test", "cross_location_test"]:
            s_data = split_transformed[s_name]
            y_true = s_data["y"]
            ts = s_data["timestamps"]

            if is_persistence:
                y_pred = model.predict(s_data["tree"])
            elif is_linear_type:
                y_pred = model.predict(s_data["linear"])
            else:
                y_pred = model.predict(s_data["tree"])

            all_predictions[model_key][s_name] = {
                "y_true": y_true,
                "y_pred": y_pred,
            }

            # Standard metrics
            split_metrics = evaluator.evaluate_split(y_true, y_pred)
            benchmark_metrics["models"][model_key][s_name] = split_metrics

            # Extremes
            benchmark_metrics["extreme_value_results"][model_key][s_name] = evaluator.evaluate_extremes(y_true, y_pred)

            # Seasons (for test split)
            if s_name == "test":
                benchmark_metrics["seasonal_results"][model_key] = evaluator.evaluate_seasons(y_true, y_pred, ts)

        # Generalization metrics
        val_m = benchmark_metrics["models"][model_key]["validation"]
        test_m = benchmark_metrics["models"][model_key]["test"]
        cross_m = benchmark_metrics["models"][model_key]["cross_location_test"]

        benchmark_metrics["temporal_generalization"][model_key] = evaluator.compute_temporal_generalization(val_m, test_m)
        benchmark_metrics["geographic_generalization"][model_key] = evaluator.compute_geographic_generalization(test_m, cross_m)

        print(f"[{model_key.upper():14s}] Fit: {model.fit_time_seconds:6.3f}s | "
              f"Test RMSE: {test_m['rmse']:6.2f} | Test MAE: {test_m['mae']:6.2f} | Test R2: {test_m['r2']:6.3f} | "
              f"Cross-Loc RMSE: {cross_m['rmse']:6.2f} | Cross-Loc R2: {cross_m['r2']:6.3f}")

    # 5. Generate Visual Diagnostics
    print("\n--- Generating Benchmark Diagnostics ---")
    generate_all_diagnostics(all_predictions, benchmark_metrics, diag_dir)
    print(f"Diagnostics saved to: {diag_dir.resolve()}")

    # 6. Save baseline_config.json and baseline_metrics.json
    config_dict = {
        "dataset_version": meta.get("dataset_version"),
        "feature_version": meta.get("feature_version"),
        "target": loader.target_name,
        "forecast_horizon": "1 hour",
        "feature_list": OPERATIONAL_FEATURES,
        "models": {k: m.get_config() for k, m in models.items()},
        "random_seed": args.seed,
        "split_sample_counts": {s: len(prepared[s]["y"]) for s in prepared},
        "environment": benchmark_metrics["environment"],
    }
    # Deterministic configuration hash
    cfg_json = json.dumps(config_dict, sort_keys=True, default=str)
    config_dict["configuration_hash"] = hashlib.sha256(cfg_json.encode("utf-8")).hexdigest()
    benchmark_metrics["reproducibility"] = {
        "configuration_hash": config_dict["configuration_hash"],
        "random_seed": args.seed,
    }

    with open(out_dir / "baseline_config.json", "w", encoding="utf-8") as f:
        json.dump(config_dict, f, indent=2, default=str)

    with open(out_dir / "baseline_metrics.json", "w", encoding="utf-8") as f:
        json.dump(benchmark_metrics, f, indent=2, default=str)

    print("\n--- Benchmark Artifacts Written ---")
    print(f"  - {out_dir / 'baseline_config.json'}")
    print(f"  - {out_dir / 'baseline_metrics.json'}")

    # 7. Print Model Comparison Table
    print("\n=========================================================================================================")
    print("                                   MODEL BASELINE BENCHMARK COMPARISON                                   ")
    print("=========================================================================================================")
    print(f"{'Model':<16} | {'Test MAE':>9} | {'Test RMSE':>9} | {'Test R2':>8} | {'Cross MAE':>9} | {'Cross RMSE':>10} | {'Cross R2':>8}")
    print("---------------------------------------------------------------------------------------------------------")
    for m_key in models:
        tm = benchmark_metrics["models"][m_key]["test"]
        cm = benchmark_metrics["models"][m_key]["cross_location_test"]
        print(f"{m_key:<16} | {tm['mae']:9.2f} | {tm['rmse']:9.2f} | {tm['r2']:8.3f} | {cm['mae']:9.2f} | {cm['rmse']:10.2f} | {cm['r2']:8.3f}")
    print("=========================================================================================================\n")


if __name__ == "__main__":
    main()
