# -*- coding: utf-8 -*-
"""Benchmark scenario definitions.

This module defines the eight controlled benchmark scenarios required for Phase 4/5.
Each scenario is represented by a :class:`Scenario` dataclass containing a human‑readable
name and a configuration dictionary that can be fed directly to the AtmosSim
physics engines (plume or puff). The configuration keys mirror the public API
of the existing simulation input builder (`SimulationInput`) so that no duplicate
physics code is introduced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Scenario:
    """Container for a benchmark scenario.

    Attributes
    ----------
    name: str
        Human‑readable identifier used in reports and diagnostics.
    config: Dict
        Dictionary of parameters required to build a ``SimulationInput``.
        The keys follow the same naming convention as the production
        ``SimulationInput`` constructor (e.g. ``stability_class``, ``wind_profile``,
        ``sources``).  The values are intentionally generic – concrete objects are
        created by the benchmark runner using the existing core factories.
    """

    name: str
    config: Dict


def _base_config() -> Dict:
    """Return a minimal base configuration shared by all scenarios.

    This includes a flat terrain, generic source metadata and a placeholder
    coordinate system.  Individual scenarios extend or override these values.
    """
    return {
        "coordinate_system": "UTM",
        "terrain": "flat",
        "domain_radius_km": 50,
        "pollutant": "PM2.5",
        "stability_class": "D",
        "wind_profile": {"type": "constant", "speed": 3.0, "direction": 90},
        "sources": [{"type": "point", "location": (0.0, 0.0), "height_m": 10, "emission_rate_g_s": 1.0}],
    }


def _scenario(name: str, overrides: Dict) -> Scenario:
    cfg = _base_config().copy()
    cfg.update(overrides)
    return Scenario(name=name, config=cfg)


def get_predefined_scenarios() -> List[Scenario]:
    """Create the eight controlled benchmark scenarios.

    Returns
    -------
    List[Scenario]
        Scenarios in the order required by the specification.
    """
    return [
        _scenario("steady_state_neutral", {"stability_class": "D", "wind_profile": {"type": "constant", "speed": 3.0, "direction": 90}}),
        _scenario("unstable_atmosphere", {"stability_class": "A", "wind_profile": {"type": "constant", "speed": 4.0, "direction": 45}}),
        _scenario("stable_atmosphere", {"stability_class": "F", "wind_profile": {"type": "constant", "speed": 2.0, "direction": 135}}),
        _scenario("time_varying_emissions", {"stability_class": "D", "wind_profile": {"type": "constant", "speed": 3.0, "direction": 90}, "emission_profile": {"type": "time_series", "values": [(0, 0.5), (3600, 1.5), (7200, 1.0)]}}),
        _scenario("rotating_wind", {"stability_class": "D", "wind_profile": {"type": "rotating", "speed": 3.0, "initial_direction": 0, "rotation_rate_deg_h": 30}}),
        _scenario("wind_reversal", {"stability_class": "D", "wind_profile": {"type": "piecewise", "segments": [{"duration_s": 7200, "speed": 3.0, "direction": 90}, {"duration_s": 7200, "speed": 3.0, "direction": 270}]}}),
        _scenario("multi_source", {"stability_class": "D", "wind_profile": {"type": "constant", "speed": 3.0, "direction": 90}, "sources": [{"type": "point", "location": (-0.001, 0.0), "height_m": 10, "emission_rate_g_s": 1.0}, {"type": "point", "location": (0.001, 0.0), "height_m": 10, "emission_rate_g_s": 0.8}]}),
        _scenario("near_source_regime", {"stability_class": "D", "wind_profile": {"type": "constant", "speed": 3.0, "direction": 90}, "sources": [{"type": "point", "location": (0.0, 0.0), "height_m": 10, "emission_rate_g_s": 1.0}], "receptor_distances_m": [50, 500, 15000]}),
    ]


__all__ = ["Scenario", "get_predefined_scenarios"]
