"""Scenario definitions and region handling for the benchmark dataset.

This module provides:
* ``Region`` – a dataclass describing a metropolitan region.
* ``BenchmarkScenario`` – a lightweight container for a single simulation configuration.
* ``get_predefined_regions`` – returns a list of hard‑coded ``Region`` objects.
* ``generate_benchmark_scenarios`` – deterministic scenario generator that produces a list of ``BenchmarkScenario``
  objects covering the diverse meteorological and emission regimes required by Phase 6.

The implementation is deliberately lightweight: it does **not** perform any simulation itself; it only
produces configuration dictionaries compatible with ``SimulationInput.from_dict`` used elsewhere in the
code‑base.
"""

from __future__ import annotations

import dataclasses
import itertools
import random
from typing import List, Dict, Any

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Region:
    """Metadata for a metropolitan region.

    Attributes
    ----------
    region_id: str – Unique identifier.
    region_name: str – Human readable name.
    country: str – ISO‑3166‑1 alpha‑2 code.
    bounding_box: tuple[float, float, float, float]
        (min_lon, min_lat, max_lon, max_lat) in WGS84 degrees.
    crs: str – Coordinate reference system identifier (e.g. "EPSG:4326").
    """

    region_id: str
    region_name: str
    country: str
    bounding_box: tuple[float, float, float, float]
    crs: str = "EPSG:4326"


@dataclasses.dataclass(frozen=True)
class BenchmarkScenario:
    """A deterministic simulation configuration.

    ``config`` is a dict that can be fed directly to
    ``SimulationInput.from_dict`` (the canonical AtmosSim factory).
    """

    region: Region
    config: Dict[str, Any]


# ---------------------------------------------------------------------------
# Helper data – a tiny hard‑coded region catalogue (extendable by the user)
# ---------------------------------------------------------------------------

_PREDEFINED_REGIONS: List[Region] = [
    Region(
        region_id="R001",
        region_name="MetroA",
        country="US",
        bounding_box=(-122.5, 37.6, -121.5, 38.2),
    ),
    Region(
        region_id="R002",
        region_name="MetroB",
        country="DE",
        bounding_box=(13.0, 52.3, 13.8, 52.7),
    ),
]


def get_predefined_regions() -> List[Region]:
    """Return the list of regions known to the dataset generator.

    The list is static; callers can extend it by concatenating additional
    ``Region`` objects if they wish to create custom benchmarks.
    """

    return list(_PREDEFINED_REGIONS)


# ---------------------------------------------------------------------------
# Scenario generation utilities
# ---------------------------------------------------------------------------

# Parameter grids – deliberately small but covering the required diversity.
_WIND_SPEEDS = [1.0, 5.0, 10.0]  # m/s
_WIND_DIRECTIONS = [0, 90, 180, 270]  # degrees
_STABILITY_CLASSES = ["A", "D", "F"]  # very unstable, neutral, very stable
_SOURCE_STRENGTHS = [0.5, 1.0, 2.0]  # g/s (example)


def _scenario_config(region: Region, wind_speed: float, wind_dir: float, stability: str, source_strength: float) -> Dict[str, Any]:
    """Construct a minimal ``SimulationInput`` configuration dictionary.

    The fields mirror the structure used elsewhere in the repository – we only
    include the keys needed for a deterministic run of the canonical simulator.
    """

    return {
        "coordinate_system": "UTM",
        "terrain": "flat",
        "domain_radius_km": 50,
        "pollutant": "PM2.5",
        "stability_class": stability,
        "wind_profile": {
            "type": "constant",
            "speed": wind_speed,
            "direction": wind_dir,
        },
        "sources": [
            {
                "type": "point",
                "location": (0.0, 0.0),
                "height_m": 10,
                "emission_rate_g_s": source_strength,
            }
        ],
        # The region metadata is attached separately; the simulation itself
        # does not need latitude/longitude because the canonical engine uses
        # a local coordinate system centred on the source.
    }


def generate_benchmark_scenarios(random_seed: int = 42) -> List[BenchmarkScenario]:
    """Deterministically generate the full list of benchmark scenarios.

    Parameters
    ----------
    random_seed: int – Seed for the internal ``random`` module so that the
        ordering of the Cartesian product is reproducible.

    Returns
    -------
    List[BenchmarkScenario]
        Each scenario is associated with one of the predefined regions and a
        configuration dict compatible with ``SimulationInput.from_dict``.
    """

    random.seed(random_seed)
    scenarios: List[BenchmarkScenario] = []

    # Cartesian product over the parameter grids. ``random.shuffle`` is applied
    # after creation to avoid any implicit ordering bias while still being
    # deterministic because the seed is fixed.
    combos = list(
        itertools.product(
            _PREDEFINED_REGIONS,
            _WIND_SPEEDS,
            _WIND_DIRECTIONS,
            _STABILITY_CLASSES,
            _SOURCE_STRENGTHS,
        )
    )
    random.shuffle(combos)

    for region, ws, wd, st, ss in combos:
        cfg = _scenario_config(region, ws, wd, st, ss)
        scenarios.append(BenchmarkScenario(region=region, config=cfg))

    return scenarios


__all__ = [
    "Region",
    "BenchmarkScenario",
    "get_predefined_regions",
    "generate_benchmark_scenarios",
]
