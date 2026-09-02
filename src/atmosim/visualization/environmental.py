"""
Diagnostic Visualization Utilities for Environmental Inputs and Source Proxies in AtmosSim.
"""

from pathlib import Path
from typing import Optional
import matplotlib.pyplot as plt
import numpy as np

from atmosim.data.open_meteo import MeteorologicalTimeSeries
from atmosim.data.terrain import TerrainField
from atmosim.simulation.input_assembler import SimulationInput


def plot_meteorological_time_series(
    time_series: MeteorologicalTimeSeries,
    output_path: Optional[Path] = None,
) -> plt.Figure:
    """Plot multi-panel meteorological time-series (Wind Speed, Direction, Temp, RH, PBLH)."""
    fig, axes = plt.subplots(4, 1, figsize=(10, 10), sharex=True)

    hours = [r.timestamp.strftime("%m-%d %H:%M") for r in time_series.records]
    x_idx = np.arange(len(hours))

    speeds = [r.wind_speed_mps for r in time_series.records]
    dirs = [r.wind_direction_deg for r in time_series.records]
    temps = [r.temperature_c for r in time_series.records]
    pblhs = [r.boundary_layer_height_m if r.boundary_layer_height_m is not None else 1000.0 for r in time_series.records]

    # Panel 1: Wind Speed
    axes[0].plot(x_idx, speeds, color="navy", lw=2, marker="o", ms=3)
    axes[0].set_ylabel("Wind Speed (m/s)")
    axes[0].grid(True, linestyle=":", alpha=0.6)
    axes[0].set_title(f"Open-Meteo Meteorology at ({time_series.latitude:.4f}°, {time_series.longitude:.4f}°)")

    # Panel 2: Wind Direction
    axes[1].scatter(x_idx, dirs, color="darkorange", s=20)
    axes[1].set_ylabel("Wind Dir (° From N)")
    axes[1].set_ylim(0, 360)
    axes[1].set_yticks([0, 90, 180, 270, 360])
    axes[1].grid(True, linestyle=":", alpha=0.6)

    # Panel 3: Temperature
    axes[2].plot(x_idx, temps, color="crimson", lw=2)
    axes[2].set_ylabel("Temp (°C)")
    axes[2].grid(True, linestyle=":", alpha=0.6)

    # Panel 4: Boundary Layer Height
    axes[3].plot(x_idx, pblhs, color="forestgreen", lw=2)
    axes[3].set_ylabel("PBLH (m)")
    axes[3].set_xlabel("Observation Time (UTC)")
    axes[3].grid(True, linestyle=":", alpha=0.6)

    step = max(1, len(x_idx) // 8)
    axes[3].set_xticks(x_idx[::step])
    axes[3].set_xticklabels(hours[::step], rotation=30, ha="right")

    plt.tight_layout()
    if output_path is not None:
        fig.savefig(output_path, dpi=200, bbox_inches="tight")
    return fig


def plot_source_network_and_terrain(
    sim_input: SimulationInput,
    output_path: Optional[Path] = None,
) -> plt.Figure:
    """Plot 2D spatial map of terrain elevation contours and road network source segments."""
    fig, ax = plt.subplots(figsize=(8, 8))

    # Terrain contours
    terrain = sim_input.terrain
    X, Y = np.meshgrid(terrain.x_coords, terrain.y_coords)
    cf = ax.contourf(X, Y, terrain.elevation_grid, levels=20, cmap="terrain", alpha=0.5)
    cbar = plt.colorbar(cf, ax=ax, shrink=0.8)
    cbar.set_label("Terrain Elevation (m a.s.l.)")

    # Road segments by class
    color_map = {
        "motorway": "red",
        "trunk": "darkorange",
        "primary": "blue",
        "secondary": "purple",
        "tertiary": "teal",
        "residential": "gray",
        "default": "black",
    }

    seen_classes = set()
    for seg in sim_input.road_segments:
        label = seg.road_class if seg.road_class not in seen_classes else None
        seen_classes.add(seg.road_class)
        c = color_map.get(seg.road_class, "black")
        sx, sy = seg.start_point_geo
        ex, ey = seg.end_point_geo
        # Use cartesian coordinates
        mx, my = seg.midpoint_cartesian
        ax.plot([mx - 50, mx + 50], [my - 50, my + 50], color=c, lw=2, label=label)

    # Simulation Domain boundary
    r = sim_input.domain_radius_m
    rect = plt.Rectangle((-r, -r), 2 * r, 2 * r, fill=False, edgecolor="black", linestyle="--", lw=1.5, label="Domain Boundary")
    ax.add_patch(rect)

    ax.set_xlabel("Cartesian East (m)")
    ax.set_ylabel("Cartesian North (m)")
    ax.set_title(f"AtmosSim Domain: Sources & Terrain ({sim_input.input_manifest['domain']['latitude']}°N, {sim_input.input_manifest['domain']['longitude']}°E)")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_aspect("equal", "box")
    ax.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()
    if output_path is not None:
        fig.savefig(output_path, dpi=200, bbox_inches="tight")
    return fig
