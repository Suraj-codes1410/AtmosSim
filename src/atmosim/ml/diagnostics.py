"""Diagnostic plots and evaluation visualizers for AtmosSim ML baselines."""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_observed_vs_predicted(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    model_name: str,
    split_name: str,
    output_path: Path,
) -> None:
    """Generate and save observed vs predicted scatter plot with 1:1 reference line."""
    plt.figure(figsize=(6, 6))
    plt.scatter(y_true, y_pred, alpha=0.4, edgecolors="none", s=20, c="#1f77b4")
    max_val = max(np.max(y_true), np.max(y_pred), 10.0) * 1.05
    plt.plot([0, max_val], [0, max_val], "r--", label="1:1 Perfect Line", linewidth=1.5)
    plt.xlim(0, max_val)
    plt.ylim(0, max_val)
    plt.xlabel("Observed PM2.5 (ug/m3)")
    plt.ylabel("Predicted PM2.5 (ug/m3)")
    plt.title(f"{model_name.upper()} - {split_name} (Observed vs Predicted)")
    plt.legend()
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_residual_distribution(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    model_name: str,
    split_name: str,
    output_path: Path,
) -> None:
    """Generate and save residual distribution histogram."""
    residuals = y_pred - y_true
    plt.figure(figsize=(7, 5))
    plt.hist(residuals, bins=30, color="#2ca02c", alpha=0.7, edgecolor="black")
    plt.axvline(0, color="red", linestyle="--", linewidth=1.5, label="Zero Bias")
    plt.axvline(np.mean(residuals), color="black", linestyle=":", linewidth=1.5, label=f"Mean Bias ({np.mean(residuals):.2f})")
    plt.xlabel("Residual (Predicted - Observed) ug/m3")
    plt.ylabel("Frequency")
    plt.title(f"{model_name.upper()} - {split_name} (Residual Distribution)")
    plt.legend()
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_model_comparison_bar(
    metrics_summary: Dict[str, Dict[str, float]],
    metric_name: str,
    output_path: Path,
) -> None:
    """Generate grouped comparison bar chart for all models across test & cross-location test."""
    models = list(metrics_summary.keys())
    test_vals = [metrics_summary[m].get("test", {}).get(metric_name, 0.0) for m in models]
    cross_vals = [metrics_summary[m].get("cross_location_test", {}).get(metric_name, 0.0) for m in models]

    x = np.arange(len(models))
    width = 0.35

    plt.figure(figsize=(10, 5))
    plt.bar(x - width/2, test_vals, width, label="Test Split", color="#1f77b4")
    plt.bar(x + width/2, cross_vals, width, label="Cross-Location Test", color="#ff7f0e")

    plt.ylabel(metric_name.upper())
    plt.title(f"Model Baseline Comparison - {metric_name.upper()}")
    plt.xticks(x, [m.replace("_", " ").title() for m in models], rotation=25)
    plt.legend()
    plt.grid(axis="y", linestyle=":", alpha=0.6)
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close()


def generate_all_diagnostics(
    models_predictions: Dict[str, Dict[str, Dict[str, np.ndarray]]],
    benchmark_metrics: Dict[str, Any],
    output_dir: Path,
) -> None:
    """Generate all baseline benchmark visual diagnostics."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Overall model comparison bar charts
    plot_model_comparison_bar(benchmark_metrics["models"], "rmse", output_dir / "comparison_rmse.png")
    plot_model_comparison_bar(benchmark_metrics["models"], "mae", output_dir / "comparison_mae.png")
    plot_model_comparison_bar(benchmark_metrics["models"], "r2", output_dir / "comparison_r2.png")

    # 2. Scatter & residual plots for each model on test split
    for model_name, split_data in models_predictions.items():
        if "test" in split_data:
            y_t = split_data["test"]["y_true"]
            y_p = split_data["test"]["y_pred"]
            plot_observed_vs_predicted(
                y_t, y_p, model_name, "test", output_dir / f"{model_name}_test_scatter.png"
            )
            plot_residual_distribution(
                y_t, y_p, model_name, "test", output_dir / f"{model_name}_test_residuals.png"
            )


__all__ = [
    "plot_observed_vs_predicted",
    "plot_residual_distribution",
    "plot_model_comparison_bar",
    "generate_all_diagnostics",
]
