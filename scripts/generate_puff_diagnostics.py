#!/usr/bin/env python3
"""
Generate publication-quality diagnostic plots for Phase 1 Gaussian Puff Engine experiments.
"""

import os
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from atmosim.physics.stability import StabilityClass
from atmosim.physics.dispersion import EnvironmentType
from atmosim.physics.puff import (
    GaussianPuffEngine,
    GaussianPuffConfig,
    EmissionSource,
    WindField,
)
from atmosim.physics.puff_lifecycle import PuffLifecycleConfig, SpatialBounds
from atmosim.visualization.puff import (
    plot_puff_trajectories,
    plot_puff_dispersion_growth,
    plot_puff_concentration_field,
    plot_puff_lifecycle_dynamics,
)


def main():
    plots_dir = repo_root / "sample_plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating Phase 1 diagnostic plots in: {plots_dir}")

    # Experiment 1: Single Continuous Source + Constant Wind
    print("Experiment 1: puff_single_constant_wind.png ...")
    cfg1 = GaussianPuffConfig(time_step=5.0, stability=StabilityClass.D)
    eng1 = GaussianPuffEngine(config=cfg1)
    eng1.add_source(EmissionSource(source_id="S1", x=0, y=0, z=30, emission_rate=100.0, release_interval=10.0))
    wind1 = WindField.from_meteorological(speed=5.0, direction_from_deg=225.0)  # SW wind -> blows to NE (+u, +v)
    eng1.run(duration=600.0, wind=wind1)

    fig1 = plot_puff_concentration_field(
        eng1,
        x_range=(-500, 3000),
        y_range=(-500, 3000),
        title="Simulated Gaussian Puff Continuous Plume (Constant SW Wind $u=5$ m/s, Class D)",
        save_path=str(plots_dir / "puff_single_constant_wind.png"),
    )
    plt.close("all")

    # Experiment 2: Variable / Rotating Wind
    print("Experiment 2: puff_rotating_wind.png ...")
    # Wind slowly rotates clockwise: direction(t) = 180 + 0.1 * t
    wind_rot = WindField(
        u_func=lambda x, y, z, t: 4.0 * np.sin(0.003 * t),
        v_func=lambda x, y, z, t: 4.0 * np.cos(0.003 * t),
    )
    cfg2 = GaussianPuffConfig(time_step=5.0, stability=StabilityClass.C)
    eng2 = GaussianPuffEngine(config=cfg2)
    eng2.add_source(EmissionSource(source_id="S1", x=0, y=0, z=25, emission_rate=100.0, release_interval=10.0))
    eng2.run(duration=800.0, wind=wind_rot)

    fig2 = plot_puff_concentration_field(
        eng2,
        x_range=(-2500, 2500),
        y_range=(-1000, 3500),
        title="Simulated Gaussian Puff Curvilinear Plume (Clockwise Rotating Wind Field)",
        save_path=str(plots_dir / "puff_rotating_wind.png"),
    )
    plt.close("all")

    # Experiment 3: Wind Reversal
    print("Experiment 3: puff_wind_reversal.png ...")
    # Eastward for t < 300s, then Westward for t >= 300s
    wind_rev = WindField(
        u_func=lambda x, y, z, t: 4.0 if t < 300.0 else -4.0,
        v_func=lambda x, y, z, t: 1.0,
    )
    cfg3 = GaussianPuffConfig(time_step=5.0, stability=StabilityClass.D)
    eng3 = GaussianPuffEngine(config=cfg3)
    eng3.add_source(EmissionSource(source_id="S1", x=0, y=0, z=20, emission_rate=100.0, release_interval=10.0))
    eng3.run(duration=600.0, wind=wind_rev)

    fig3 = plot_puff_concentration_field(
        eng3,
        x_range=(-1500, 2000),
        y_range=(-200, 1000),
        title="Simulated Gaussian Puff Plume under Wind Direction Reversal ($t=300$ s)",
        save_path=str(plots_dir / "puff_wind_reversal.png"),
    )
    plt.close("all")

    # Experiment 4: Stability Growth Comparison
    print("Experiment 4: puff_stability_growth.png ...")
    plot_puff_dispersion_growth(
        stabilities=[StabilityClass.A, StabilityClass.D, StabilityClass.F],
        duration=3600.0,
        speed=4.0,
        save_path=str(plots_dir / "puff_stability_growth.png"),
    )
    plt.close("all")

    # Experiment 5: Multi-Source Superposition
    print("Experiment 5: puff_multi_source.png ...")
    cfg5 = GaussianPuffConfig(time_step=5.0, stability=StabilityClass.C)
    eng5 = GaussianPuffEngine(config=cfg5)
    eng5.add_source(EmissionSource(source_id="Industrial_Stack", x=0, y=0, z=50, emission_rate=150.0, release_interval=10.0))
    eng5.add_source(EmissionSource(source_id="Traffic_Corridor", x=800, y=-400, z=5, emission_rate=80.0, release_interval=10.0))
    eng5.add_source(EmissionSource(source_id="Power_Plant", x=-500, y=600, z=80, emission_rate=250.0, release_interval=10.0))

    wind5 = WindField.constant(u=3.5, v=1.5)
    eng5.run(duration=600.0, wind=wind5)

    fig5 = plot_puff_concentration_field(
        eng5,
        x_range=(-1000, 3500),
        y_range=(-1000, 2500),
        title="Simulated Multi-Source Gaussian Puff Dispersion & Spatial Superposition",
        save_path=str(plots_dir / "puff_multi_source.png"),
    )
    plt.close("all")

    # Experiment 6: Lifecycle Population Dynamics & Memory Boundedness
    print("Experiment 6: puff_lifecycle_memory.png ...")
    max_age = 200.0
    cfg6 = GaussianPuffConfig(
        time_step=5.0,
        lifecycle_config=PuffLifecycleConfig(max_age=max_age),
    )
    eng6 = GaussianPuffEngine(config=cfg6)
    eng6.add_source(EmissionSource(source_id="S1", x=0, y=0, z=20, emission_rate=100.0, release_interval=5.0))
    wind6 = WindField.constant(u=4.0, v=2.0)

    times = []
    created = []
    active = []
    culled = []

    for step_i in range(160):  # 800 seconds total
        eng6.step(5.0, wind6)
        times.append(eng6.current_time)
        created.append(eng6.stats.created_count)
        active.append(eng6.stats.active_count)
        culled.append(eng6.stats.culled_count)

    plot_puff_lifecycle_dynamics(
        time_series_data={"times": times, "created": created, "active": active, "culled": culled},
        save_path=str(plots_dir / "puff_lifecycle_memory.png"),
    )
    plt.close("all")

    print("All Phase 1 diagnostic plots generated successfully!")


if __name__ == "__main__":
    main()
