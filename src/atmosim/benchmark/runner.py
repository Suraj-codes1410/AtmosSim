# -*- coding: utf-8 -*-
"""Benchmark runner utilities.

The runner translates a :class:`~atmosim.benchmark.scenarios.Scenario` into a
proper ``SimulationInput`` object using the existing core factories and then
executes the requested simulator engine (``"plume"`` or ``"puff"``).  It also
contains helpers for loading pre‑generated HYSPLIT fixtures and OpenAQ test
fixtures – the functions return ``None`` in the scaffold implementation; real
logic will be added later.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .scenarios import Scenario


def build_simulation_input(scenario: Scenario) -> Any:
    """Construct a ``SimulationInput`` from a benchmark scenario.

    The concrete ``SimulationInput`` class lives in ``src/atmosim/simulation``.
    This function imports it lazily to avoid unnecessary dependencies during
    unit testing.  The implementation simply forwards the scenario ``config``
    dictionary to the factory method ``SimulationInput.from_dict`` (which must
    exist in the production code).
    """
    from atmosim.simulation.input_assembler import SimulationInput

    return SimulationInput.from_dict(scenario.config)  # type: ignore[arg-type]


def run_engine(input_obj: Any, engine: str) -> Any:
    """Execute the specified engine and return its raw output.

    Parameters
    ----------
    input_obj: Any
        A ``SimulationInput`` instance.
    engine: str
        Either ``"plume"`` or ``"puff"``.
    """
    if engine == "plume":
        from atmosim.physics.plume import GaussianPlumeModel

        model = GaussianPlumeModel(input_obj)
        return model.evaluate()
    elif engine == "puff":
        from atmosim.physics.puff import GaussianPuffEngine

        model = GaussianPuffEngine(input_obj)
        return model.evaluate()
    else:
        raise ValueError(f"Unsupported engine: {engine}")


def load_hysplit_fixture(case_id: str) -> Optional[Dict]:
    """Load an offline HYSPLIT fixture.

    The fixture files live under ``tests/fixtures/hysplit/<case_id>.json``.
    In the scaffold we simply return ``None`` – the real implementation will
    read the JSON file and return the parsed content.
    """
    return None


def load_openaq_fixture(station_id: str) -> Optional[Dict]:
    """Load an OpenAQ observation fixture.

    The fixture files live under ``tests/fixtures/openaq/<station_id>.json``.
    Stub implementation returns ``None``.
    """
    return None


__all__ = [
    "build_simulation_input",
    "run_engine",
    "load_hysplit_fixture",
    "load_openaq_fixture",
]
