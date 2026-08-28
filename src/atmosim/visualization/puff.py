import math
"""
Visualization utilities for Time-Dependent Gaussian Puff Engine.

Provides publication-grade diagnostic plots for puff trajectories, variable wind fields,
puff dispersion growth curves, 2D concentration fields, multi-source superposition,
and lifecycle population dynamics.
"""

from typing import List, Optional, Tuple
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, Normalize
import numpy as np

from atmosim.physics.stability import StabilityClass
from atmosim.physics.puff import (
    GaussianPuffEngine,
    GaussianPuffConfig,
    EmissionSource,
    WindField,
)


def plot_puff_trajectories(
    engine: GaussianPuffEngine,
    title: str = "Simulated Lagrangian Puff Center Trajectories",
    ax: Optional[plt.Axes] = None,
    save_path: Optional[str] = None,
) -> Tuple[plt.Figure, plt.Axes]:
    """Plot trajectories of active and culled puffs in the 2D Cartesian plane."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(9, 6), dpi=150)
    else:
        fig = ax.figure

    # Plot sources
    for src in engine.sources:
        ax.scatter(src.x, src.y, color="red", marker="*", s=200, edgecolors="black", zorder=6, label=f"Source ({src.source_id})")

    # Plot culled puffs (faded)
    if engine.culled_puffs:
        cx = [p.x for p in engine.culled_puffs]
        cy = [p.y for p in engine.culled_puffs]
        ax.scatter(cx, cy, color="gray", alpha=0.3, s=15, label=f"Culled Puffs (N={len(cx)})", zorder=3)

    # Plot active puffs (colored by age)
    if engine.active_puffs:
        ax_pos = [p.x for p in engine.active_puffs]
        ay_pos = [p.y for p in engine.active_puffs]
        ages = [p.age for p in engine.active_puffs]
        sc = ax.scatter(ax_pos, ay_pos, c=ages, cmap="viridis", s=45, edgecolors="black", linewidths=0.5, zorder=5, label=f"Active Puffs (N={len(ax_pos)})")
        cbar = fig.colorbar(sc, ax=ax, pad=0.02)
        cbar.set_label("Puff Age [s]", fontsize=10, fontweight="bold")

    ax.set_xlabel("Eastward Distance $x$ [m]", fontsize=11, fontweight="bold")
    ax.set_ylabel("Northward Distance $y$ [m]", fontsize=11, fontweight="bold")
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="upper right", framealpha=0.9)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    return fig, ax


def plot_puff_dispersion_growth(
    stabilities: List[StabilityClass] = [StabilityClass.A, StabilityClass.D, StabilityClass.F],
    duration: float = 3600.0,
    speed: float = 4.0,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """Plot horizontal (sigma_x=sigma_y) and vertical (sigma_z) dispersion growth vs travel time."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=150)
    wind = WindField.constant(speed, 0.0)

    palette = {
        StabilityClass.A: "#d62728",
        StabilityClass.D: "#2ca02c",
        StabilityClass.F: "#1f77b4",
    }

    for st in stabilities:
        cfg = GaussianPuffConfig(stability=st, time_step=10.0)
        eng = GaussianPuffEngine(config=cfg)
        eng.add_source(EmissionSource(source_id="src", x=0, y=0, z=20, emission_rate=100.0, release_interval=duration + 10.0))
        eng.run(duration=duration, wind=wind, dt=10.0)

        p = eng.active_puffs[0]
        # Evaluate growth curve across ages
        times = np.linspace(10.0, duration, 200)
        s_vals = speed * times
        from atmosim.physics.dispersion import compute_sigma_y, compute_sigma_z
        sy_vals = [math.hypot(1.0, float(compute_sigma_y(s, st))) for s in s_vals]
        sz_vals = [math.hypot(1.0, float(compute_sigma_z(s, st))) for s in s_vals]

        col = palette.get(st, "gray")
        ax1.plot(times, sy_vals, label=f"Class {st.value} ({st.description})", color=col, linewidth=2.0)
        ax2.plot(times, sz_vals, label=f"Class {st.value} ({st.description})", color=col, linewidth=2.0)

    ax1.set_xlabel("Puff Age / Travel Time [s]", fontsize=11, fontweight="bold")
    ax1.set_ylabel(r"Horizontal Dispersion $\sigma_x = \sigma_y$ [m]", fontsize=11, fontweight="bold")
    ax1.set_title(r"Simulated Horizontal Dispersion Growth $\sigma_y(t)$", fontsize=11, fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(fontsize=9.5)

    ax2.set_xlabel("Puff Age / Travel Time [s]", fontsize=11, fontweight="bold")
    ax2.set_ylabel(r"Vertical Dispersion $\sigma_z$ [m]", fontsize=11, fontweight="bold")
    ax2.set_title(r"Simulated Vertical Dispersion Growth $\sigma_z(t)$", fontsize=11, fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(fontsize=9.5)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    return fig


def plot_puff_concentration_field(
    engine: GaussianPuffEngine,
    x_range: Tuple[float, float] = (-2000.0, 6000.0),
    y_range: Tuple[float, float] = (-3000.0, 3000.0),
    grid_res: int = 150,
    title: str = "Simulated Gaussian Puff Ground Concentration Field",
    unit: str = r"$\mu\mathrm{g}/\mathrm{m}^3$",
    log_scale: bool = False,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """Render 2D horizontal ground-level concentration heatmap of superimposed puffs."""
    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    xs = np.linspace(x_range[0], x_range[1], grid_res)
    ys = np.linspace(y_range[0], y_range[1], grid_res)
    X, Y = np.meshgrid(xs, ys)

    C = engine.evaluate(X, Y, z_rec=0.0) * 1e6  # g/m³ to µg/m³
    c_clean = np.where(np.isfinite(C) & (C > 0), C, 0.0)

    if log_scale:
        min_pos = np.min(c_clean[c_clean > 0]) if np.any(c_clean > 0) else 1e-6
        norm = LogNorm(vmin=max(min_pos, 1e-4), vmax=max(np.max(c_clean), 1.0))
    else:
        norm = Normalize(vmin=0.0, vmax=np.max(c_clean) if np.max(c_clean) > 0 else 1.0)

    contour = ax.contourf(X, Y, c_clean, levels=100, cmap="viridis", norm=norm, extend="both" if log_scale else "max")
    cbar = fig.colorbar(contour, ax=ax, pad=0.02)
    cbar.set_label(f"Simulated Concentration [{unit}]", fontsize=11, fontweight="bold")

    # Plot sources
    for src in engine.sources:
        ax.scatter(src.x, src.y, color="red", marker="*", s=220, edgecolors="black", label=f"Source ({src.source_id})", zorder=6)

    # Plot active puff centers
    if engine.active_puffs:
        px = [p.x for p in engine.active_puffs]
        py = [p.y for p in engine.active_puffs]
        ax.scatter(px, py, color="white", marker="o", s=15, edgecolors="black", linewidths=0.5, alpha=0.7, label=f"Puff Centers (N={len(px)})", zorder=5)

    ax.set_xlabel("Eastward Distance $x$ [m]", fontsize=11, fontweight="bold")
    ax.set_ylabel("Northward Distance $y$ [m]", fontsize=11, fontweight="bold")
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="upper right", framealpha=0.9)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    return fig


def plot_puff_lifecycle_dynamics(
    time_series_data: dict,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """Plot time evolution of created, active, and culled puff counts demonstrating memory boundedness."""
    fig, ax = plt.subplots(figsize=(9, 5), dpi=150)
    times = time_series_data["times"]
    created = time_series_data["created"]
    active = time_series_data["active"]
    culled = time_series_data["culled"]

    ax.plot(times, created, label="Cumulative Created Puffs", color="#1f77b4", linewidth=2.0, linestyle="--")
    ax.plot(times, culled, label="Cumulative Culled Puffs", color="#d62728", linewidth=2.0, linestyle=":")
    ax.plot(times, active, label="Active Memory Population", color="#2ca02c", linewidth=2.5)

    ax.set_xlabel("Simulation Time [s]", fontsize=11, fontweight="bold")
    ax.set_ylabel("Puff Count", fontsize=11, fontweight="bold")
    ax.set_title("Simulated Puff Population Lifecycle & Memory Boundedness Dynamics", fontsize=11, fontweight="bold", pad=10)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(fontsize=10, loc="center right", framealpha=0.95)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    return fig
