#!/usr/bin/env python3
"""
Generate publication-quality diagnostic plots for Phase 0 Gaussian Plume baseline.
"""

import os
import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

from atmosim.physics.stability import StabilityClass
from atmosim.physics.dispersion import EnvironmentType
from atmosim.physics.plume import GaussianPlumeModel
from atmosim.visualization.plume import (
    plot_plume_2d,
    plot_stability_comparison,
    plot_wind_comparison,
    plot_emission_comparison,
    plot_crosswind_slice,
    plot_downwind_centerline,
)


def main():
    plots_dir = repo_root / "sample_plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating Phase 0 diagnostic plots in: {plots_dir}")

    # Plot 1: Gaussian Plume Baseline 2D field
    print("Generating Plot 1: gaussian_plume_baseline.png ...")
    model = GaussianPlumeModel(
        Q=100.0,            # 100 g/s
        wind_speed=4.0,     # 4 m/s
        effective_height=30.0, # 30 m stack
        stability=StabilityClass.D,
        environment=EnvironmentType.RURAL,
    )
    xs = np.linspace(100.0, 5000.0, 200)
    ys = np.linspace(-500.0, 500.0, 200)
    x_grid, y_grid = np.meshgrid(xs, ys)
    c_field = model.evaluate(x_grid, y_grid, z=0.0) * 1e6  # convert g/m³ to µg/m³

    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)
    plot_plume_2d(
        x_grid,
        y_grid,
        c_field,
        title="Simulated Gaussian Plume Baseline — Class D (Neutral) | Q=100 g/s, u=4 m/s, H=30 m",
        unit=r"$\mu\mathrm{g}/\mathrm{m}^3$",
        ax=ax,
    )
    fig.savefig(plots_dir / "gaussian_plume_baseline.png", bbox_inches="tight")
    plt.close(fig)

    # Plot 2: Stability Comparison (Classes A, D, F)
    print("Generating Plot 2: stability_comparison.png ...")
    plot_stability_comparison(
        stabilities=[StabilityClass.A, StabilityClass.D, StabilityClass.F],
        Q=100.0,
        wind_speed=4.0,
        effective_height=30.0,
        save_path=str(plots_dir / "stability_comparison.png"),
    )
    plt.close("all")

    # Plot 3: Wind Speed Comparison (2, 5, 10 m/s)
    print("Generating Plot 3: wind_comparison.png ...")
    plot_wind_comparison(
        wind_speeds=[2.0, 5.0, 10.0],
        stability=StabilityClass.D,
        Q=100.0,
        effective_height=30.0,
        save_path=str(plots_dir / "wind_comparison.png"),
    )
    plt.close("all")

    # Plot 4: Emission Rate Comparison (0.5Q, Q, 2Q = 50, 100, 200 g/s)
    print("Generating Plot 4: emission_comparison.png ...")
    plot_emission_comparison(
        emission_rates=[50.0, 100.0, 200.0],
        wind_speed=4.0,
        stability=StabilityClass.C,
        effective_height=30.0,
        save_path=str(plots_dir / "emission_comparison.png"),
    )
    plt.close("all")

    # Plot 5: Crosswind Slice C(y) at multiple downwind distances
    print("Generating Plot 5: crosswind_slice.png ...")
    plot_crosswind_slice(
        downwind_distances=[500.0, 1000.0, 2000.0, 4000.0],
        Q=100.0,
        wind_speed=4.0,
        effective_height=30.0,
        stability=StabilityClass.D,
        save_path=str(plots_dir / "crosswind_slice.png"),
    )
    plt.close("all")

    # Plot 6: Downwind Centerline C(x, y=0, z=0) across all 6 classes (A-F)
    print("Generating Plot 6: downwind_centerline.png ...")
    plot_downwind_centerline(
        stabilities=[
            StabilityClass.A,
            StabilityClass.B,
            StabilityClass.C,
            StabilityClass.D,
            StabilityClass.E,
            StabilityClass.F,
        ],
        Q=100.0,
        wind_speed=4.0,
        effective_height=30.0,
        save_path=str(plots_dir / "downwind_centerline.png"),
    )
    plt.close("all")

    print("All Phase 0 diagnostic plots generated successfully!")


if __name__ == "__main__":
    main()
