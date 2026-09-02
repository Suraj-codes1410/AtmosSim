#!/usr/bin/env python3
"""
Phase 2 Environmental & Source Ingestion Diagnostic Generator for AtmosSim.

Demonstrates end-to-end assembly of general-location inputs (meteorology, terrain, OSM sources),
generates multi-panel diagnostic figures, and executes a test simulation with the Phase 1 Puff Engine.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
import json
import matplotlib.pyplot as plt
import numpy as np

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from atmosim.data.cache import DataCache
from atmosim.data.open_meteo import OpenMeteoConnector
from atmosim.data.overpass import OverpassConnector
from atmosim.data.terrain import TerrainConnector, TerrainField
from atmosim.physics.puff import GaussianPuffConfig
from atmosim.simulation.input_assembler import SimulationInputAssembler
from atmosim.visualization.environmental import (
    plot_meteorological_time_series,
    plot_source_network_and_terrain,
)


def main():
    output_dir = Path("/home/suraj/AtmosSim/sample_plots")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating Phase 2 Environmental & Source Ingestion Diagnostics...")

    cache = DataCache(cache_dir=Path(".cache/atmosim"))

    # Load fixtures
    with open("/home/suraj/AtmosSim/tests/fixtures/sample_open_meteo.json", "r") as f:
        meteo_data = json.load(f)
    with open("/home/suraj/AtmosSim/tests/fixtures/sample_overpass_roads.json", "r") as f:
        osm_data = json.load(f)

    meteo_conn = OpenMeteoConnector(cache=cache)
    terrain_conn = TerrainConnector(cache=cache)
    overpass_conn = OverpassConnector(cache=cache)

    assembler = SimulationInputAssembler(
        cache=cache,
        meteo_connector=meteo_conn,
        terrain_connector=terrain_conn,
        overpass_connector=overpass_conn,
    )

    # Monkeypatch to use offline fixtures
    meteo_conn.fetch_meteorology = lambda latitude, longitude, start_time, end_time, **kwargs: meteo_conn.parse_response(
        raw_json=meteo_data, latitude=latitude, longitude=longitude, start_time=start_time, end_time=end_time,
    )
    overpass_conn.fetch_features = lambda min_lat, min_lon, max_lat, max_lon, **kwargs: overpass_conn.parse_response(
        raw_json=osm_data
    )

    # 1. Assemble Delhi Simulation Input
    sim_input = assembler.build(
        latitude=28.6139,
        longitude=77.2090,
        start_time=datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc),
        domain_radius_m=3000.0,
        terrain_resolution_m=250.0,
    )

    # 2. Generate Diagnostic Plot 1: Meteorology Time Series
    p1 = output_dir / "phase2_meteo_timeseries.png"
    print(f"Generating {p1.name} ...")
    plot_meteorological_time_series(sim_input.meteorology, output_path=p1)
    plt.close("all")

    # 3. Generate Diagnostic Plot 2: Source Network & Terrain Elevation
    p2 = output_dir / "phase2_sources_and_terrain.png"
    print(f"Generating {p2.name} ...")
    plot_source_network_and_terrain(sim_input, output_path=p2)
    plt.close("all")

    # 4. Generate Diagnostic Plot 3: Puff Engine Simulation Snapshot
    p3 = output_dir / "phase2_puff_simulation_snapshot.png"
    print(f"Generating {p3.name} ...")
    engine = sim_input.to_puff_engine(config=GaussianPuffConfig(time_step=2.0))
    wind = sim_input.get_wind_field()

    # Step simulation for 120 seconds
    engine.run(duration=120.0, wind=wind, dt=2.0)

    # Evaluate ground concentration
    xs = np.linspace(-3000, 3000, 100)
    ys = np.linspace(-3000, 3000, 100)
    X, Y = np.meshgrid(xs, ys)
    Z = np.zeros_like(X)
    conc = engine.evaluate(X.ravel(), Y.ravel(), Z.ravel()).reshape(X.shape)

    fig, ax = plt.subplots(figsize=(8, 7))
    cf = ax.contourf(X, Y, conc * 1e6, levels=30, cmap="viridis")  # ug/m3
    cbar = plt.colorbar(cf, ax=ax)
    cbar.set_label("Surface PM2.5 Concentration (μg/m³)")

    # Plot road segments
    for seg in sim_input.road_segments:
        mx, my = seg.midpoint_cartesian
        ax.plot([mx - 40, mx + 40], [my - 40, my + 40], color="red", lw=1.5, alpha=0.7)

    # Plot active puff centers
    px = [p.x for p in engine.active_puffs]
    py = [p.y for p in engine.active_puffs]
    ax.scatter(px, py, color="magenta", s=15, edgecolor="black", label=f"Active Puffs (N={len(px)})")

    ax.set_xlabel("Cartesian East (m)")
    ax.set_ylabel("Cartesian North (m)")
    ax.set_title("AtmosSim Phase 2: Multi-Source Puff Dispersion Field")
    ax.set_aspect("equal", "box")
    ax.legend(loc="upper right")
    ax.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()
    fig.savefig(p3, dpi=200, bbox_inches="tight")
    plt.close("all")

    print("All Phase 2 diagnostic plots generated successfully!")


if __name__ == "__main__":
    main()
