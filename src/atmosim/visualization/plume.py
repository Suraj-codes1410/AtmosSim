"""
Visualization functions for Gaussian Plume baseline diagnostic evaluation.

Provides publication-grade diagnostic plotting tools with standardized physical annotations,
scientific colormaps, units, and clear labeling indicating simulated output.
"""

from typing import List, Optional, Tuple, Union
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, Normalize
import numpy as np

from atmosim.physics.stability import StabilityClass
from atmosim.physics.dispersion import EnvironmentType
from atmosim.physics.plume import GaussianPlumeModel, gaussian_plume_concentration


def plot_plume_2d(
    x_grid: np.ndarray,
    y_grid: np.ndarray,
    concentration: np.ndarray,
    source_location: Tuple[float, float] = (0.0, 0.0),
    title: str = "Simulated Gaussian Plume Concentration Field",
    unit: str = r"$\mu\mathrm{g}/\mathrm{m}^3$",
    log_scale: bool = False,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    ax: Optional[plt.Axes] = None,
    cmap: str = "viridis",
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Render a 2D horizontal concentration heatmap of simulated dispersion.

    Parameters
    ----------
    x_grid : np.ndarray
        2D meshgrid of downwind coordinates in meters.
    y_grid : np.ndarray
        2D meshgrid of crosswind coordinates in meters.
    concentration : np.ndarray
        2D array of concentration values matching grid shape.
    source_location : Tuple[float, float], default=(0, 0)
        (x, y) location of the emission source in meters.
    title : str
        Plot title. Must indicate modeled/simulated output.
    unit : str
        Concentration unit label for colorbar.
    log_scale : bool
        Whether to display concentration using logarithmic color normalization.
    vmin, vmax : float, optional
        Colorbar scale limits.
    ax : plt.Axes, optional
        Existing matplotlib axes to draw on.
    cmap : str
        Colormap name.

    Returns
    -------
    Tuple[plt.Figure, plt.Axes]
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    else:
        fig = ax.figure

    conc_clean = np.where(np.isfinite(concentration) & (concentration > 0), concentration, 0.0)

    if log_scale:
        min_pos = np.min(conc_clean[conc_clean > 0]) if np.any(conc_clean > 0) else 1e-6
        c_vmin = vmin if vmin is not None else min_pos
        c_vmax = vmax if vmax is not None else (np.max(conc_clean) if np.max(conc_clean) > 0 else 1.0)
        norm = LogNorm(vmin=max(c_vmin, 1e-12), vmax=max(c_vmax, 1e-11))
    else:
        c_vmin = vmin if vmin is not None else 0.0
        c_vmax = vmax if vmax is not None else np.max(conc_clean)
        norm = Normalize(vmin=c_vmin, vmax=c_vmax)

    contour = ax.contourf(
        x_grid,
        y_grid,
        conc_clean,
        levels=100,
        cmap=cmap,
        norm=norm,
        extend="both" if log_scale else "max",
    )

    cbar = fig.colorbar(contour, ax=ax, pad=0.02)
    cbar.set_label(f"Simulated Concentration [{unit}]", fontsize=11, fontweight="bold")

    # Source location marker
    ax.scatter(
        [source_location[0]],
        [source_location[1]],
        color="red",
        marker="*",
        s=180,
        edgecolors="black",
        linewidths=1.2,
        label="Emission Source",
        zorder=5,
    )

    # Wind direction vector annotation
    x_min, x_max = np.min(x_grid), np.max(x_grid)
    y_min, y_max = np.min(y_grid), np.max(y_grid)
    arrow_start_x = x_min + 0.08 * (x_max - x_min)
    arrow_start_y = y_max - 0.12 * (y_max - y_min)
    arrow_len_x = 0.12 * (x_max - x_min)
    ax.annotate(
        "Wind Vector",
        xy=(arrow_start_x + arrow_len_x, arrow_start_y),
        xytext=(arrow_start_x, arrow_start_y),
        arrowprops=dict(facecolor="white", edgecolor="black", width=2, headwidth=8),
        fontsize=9,
        fontweight="bold",
        color="black",
        va="center",
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8, edgecolor="gray"),
    )

    ax.set_xlabel("Downwind Distance $x$ [m]", fontsize=11, fontweight="bold")
    ax.set_ylabel("Crosswind Coordinate $y$ [m]", fontsize=11, fontweight="bold")
    ax.set_title(title, fontsize=12, fontweight="bold", pad=12)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="upper right", framealpha=0.9)

    fig.tight_layout()
    return fig, ax


def plot_stability_comparison(
    stabilities: List[StabilityClass] = [StabilityClass.A, StabilityClass.D, StabilityClass.F],
    Q: float = 100.0,
    wind_speed: float = 4.0,
    effective_height: float = 30.0,
    x_range: Tuple[float, float] = (100.0, 5000.0),
    y_range: Tuple[float, float] = (-500.0, 500.0),
    grid_res: int = 150,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """Plot multi-panel comparison of concentration plumes across stability classes."""
    fig, axes = plt.subplots(len(stabilities), 1, figsize=(11, 3.8 * len(stabilities)), dpi=150)
    if len(stabilities) == 1:
        axes = [axes]

    xs = np.linspace(x_range[0], x_range[1], grid_res)
    ys = np.linspace(y_range[0], y_range[1], grid_res)
    x_grid, y_grid = np.meshgrid(xs, ys)

    # Common max for consistent comparison colorbar
    max_c = 0.0
    concs = []
    for st in stabilities:
        model = GaussianPlumeModel(
            Q=Q,
            wind_speed=wind_speed,
            effective_height=effective_height,
            stability=st,
        )
        c = model.evaluate(x_grid, y_grid, z=0.0)
        concs.append(c)
        max_c = max(max_c, float(np.max(c)))

    for ax, st, c in zip(axes, stabilities, concs):
        plot_plume_2d(
            x_grid,
            y_grid,
            c,
            title=f"Simulated Plume — Pasquill Stability Class {st.value} ({st.description}) | Q={Q} g/s, u={wind_speed} m/s, H={effective_height} m",
            vmax=max_c,
            ax=ax,
        )

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    return fig


def plot_wind_comparison(
    wind_speeds: List[float] = [2.0, 5.0, 10.0],
    stability: StabilityClass = StabilityClass.D,
    Q: float = 100.0,
    effective_height: float = 30.0,
    x_range: Tuple[float, float] = (100.0, 5000.0),
    y_range: Tuple[float, float] = (-500.0, 500.0),
    grid_res: int = 150,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """Plot multi-panel comparison showing the inverse wind-speed dilution effect."""
    fig, axes = plt.subplots(len(wind_speeds), 1, figsize=(11, 3.8 * len(wind_speeds)), dpi=150)
    if len(wind_speeds) == 1:
        axes = [axes]

    xs = np.linspace(x_range[0], x_range[1], grid_res)
    ys = np.linspace(y_range[0], y_range[1], grid_res)
    x_grid, y_grid = np.meshgrid(xs, ys)

    for ax, u in zip(axes, wind_speeds):
        model = GaussianPlumeModel(
            Q=Q,
            wind_speed=u,
            effective_height=effective_height,
            stability=stability,
        )
        c = model.evaluate(x_grid, y_grid, z=0.0)
        plot_plume_2d(
            x_grid,
            y_grid,
            c,
            title=f"Simulated Plume Wind-Speed Dilution Effect — Wind Speed u = {u} m/s (Class {stability.value}, Q={Q} g/s, H={effective_height} m)",
            ax=ax,
        )

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    return fig


def plot_emission_comparison(
    emission_rates: List[float] = [50.0, 100.0, 200.0],
    wind_speed: float = 4.0,
    stability: StabilityClass = StabilityClass.C,
    effective_height: float = 30.0,
    x_range: Tuple[float, float] = (100.0, 5000.0),
    y_range: Tuple[float, float] = (-500.0, 500.0),
    grid_res: int = 150,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """Plot multi-panel comparison showing linear emission rate scaling."""
    fig, axes = plt.subplots(len(emission_rates), 1, figsize=(11, 3.8 * len(emission_rates)), dpi=150)
    if len(emission_rates) == 1:
        axes = [axes]

    xs = np.linspace(x_range[0], x_range[1], grid_res)
    ys = np.linspace(y_range[0], y_range[1], grid_res)
    x_grid, y_grid = np.meshgrid(xs, ys)

    for ax, q in zip(axes, emission_rates):
        model = GaussianPlumeModel(
            Q=q,
            wind_speed=wind_speed,
            effective_height=effective_height,
            stability=stability,
        )
        c = model.evaluate(x_grid, y_grid, z=0.0)
        plot_plume_2d(
            x_grid,
            y_grid,
            c,
            title=f"Simulated Plume Emission Scaling — Emission Rate Q = {q} g/s (Class {stability.value}, u={wind_speed} m/s, H={effective_height} m)",
            ax=ax,
        )

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    return fig


def plot_crosswind_slice(
    downwind_distances: List[float] = [500.0, 1000.0, 2000.0, 4000.0],
    Q: float = 100.0,
    wind_speed: float = 4.0,
    effective_height: float = 30.0,
    stability: StabilityClass = StabilityClass.D,
    y_range: Tuple[float, float] = (-800.0, 800.0),
    save_path: Optional[str] = None,
) -> plt.Figure:
    """Plot 1D crosswind concentration profiles C(y) at selected downwind distances."""
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=150)
    ys = np.linspace(y_range[0], y_range[1], 400)
    model = GaussianPlumeModel(
        Q=Q,
        wind_speed=wind_speed,
        effective_height=effective_height,
        stability=stability,
    )

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    for x_val, col in zip(downwind_distances, colors):
        c = model.evaluate(x=x_val, y=ys, z=0.0)
        sy, sz = model.compute_sigmas(x_val)
        ax.plot(
            ys,
            c * 1e6,  # convert to ug/m3 for display
            label=rf"$x = {int(x_val)}$ m ($\sigma_y={sy:.1f}$ m, $\sigma_z={sz:.1f}$ m)",
            color=col,
            linewidth=2.0,
        )

    ax.set_xlabel("Crosswind Coordinate $y$ [m]", fontsize=11, fontweight="bold")
    ax.set_ylabel(r"Simulated Ground Concentration [$\mu\mathrm{g}/\mathrm{m}^3$]", fontsize=11, fontweight="bold")
    ax.set_title(
        f"Simulated Crosswind Dispersion Slices $C(y)$ (Class {stability.value}, Q={Q} g/s, u={wind_speed} m/s, H={effective_height} m)",
        fontsize=11,
        fontweight="bold",
        pad=10,
    )
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(fontsize=10, framealpha=0.95)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    return fig


def plot_downwind_centerline(
    stabilities: List[StabilityClass] = [
        StabilityClass.A,
        StabilityClass.B,
        StabilityClass.C,
        StabilityClass.D,
        StabilityClass.E,
        StabilityClass.F,
    ],
    Q: float = 100.0,
    wind_speed: float = 4.0,
    effective_height: float = 30.0,
    x_range: Tuple[float, float] = (100.0, 10000.0),
    save_path: Optional[str] = None,
) -> plt.Figure:
    """Plot ground-level centerline concentration C(x, y=0, z=0) versus downwind distance x for all stability classes."""
    fig, ax = plt.subplots(figsize=(9.5, 6), dpi=150)
    xs = np.linspace(x_range[0], x_range[1], 500)

    palette = {
        StabilityClass.A: "#d62728",  # Red (extremely unstable)
        StabilityClass.B: "#ff7f0e",  # Orange
        StabilityClass.C: "#bcbd22",  # Yellow-green
        StabilityClass.D: "#2ca02c",  # Green (neutral)
        StabilityClass.E: "#17becf",  # Cyan
        StabilityClass.F: "#1f77b4",  # Blue (extremely stable)
    }

    for st in stabilities:
        model = GaussianPlumeModel(
            Q=Q,
            wind_speed=wind_speed,
            effective_height=effective_height,
            stability=st,
        )
        c = model.evaluate(x=xs, y=0.0, z=0.0)
        ax.plot(
            xs,
            c * 1e6,  # convert to ug/m3
            label=f"Class {st.value} ({st.description})",
            color=palette.get(st, "gray"),
            linewidth=2.2,
        )

    ax.set_xlabel("Downwind Distance $x$ [m]", fontsize=11, fontweight="bold")
    ax.set_ylabel(r"Simulated Ground Centerline Concentration [$\mu\mathrm{g}/\mathrm{m}^3$]", fontsize=11, fontweight="bold")
    ax.set_title(
        f"Simulated Downwind Centerline Dispersion $C(x, y=0, z=0)$\n(Q={Q} g/s, u={wind_speed} m/s, Effective Stack Height H={effective_height} m)",
        fontsize=11,
        fontweight="bold",
        pad=10,
    )
    ax.set_yscale("log")
    ax.grid(True, which="both", linestyle="--", alpha=0.5)
    ax.legend(fontsize=9.5, loc="upper right", framealpha=0.95)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    return fig
