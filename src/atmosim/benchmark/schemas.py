# -*- coding: utf-8 -*-
"""JSON schemas for benchmark artifacts.

Only the schema for ``simulator_metrics.json`` is defined here.  The schema is
intended for validation of the final artifact and mirrors the structure
specified in the Phase 4/5 documentation.
"""

from __future__ import annotations

import json
from typing import Any, Dict


SIMULATOR_METRICS_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "AtmosSim Simulator Metrics",
    "type": "object",
    "required": ["benchmark_version", "timestamp", "candidates", "weights", "canonical_simulator", "selection_status", "selection_method"],
    "properties": {
        "benchmark_version": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "candidates": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["physics", "real_data", "extreme_events", "robustness", "generalization", "efficiency", "weighted_score"],
                "properties": {
                    "physics": {"type": "number"},
                    "real_data": {"type": "number"},
                    "extreme_events": {"type": "number"},
                    "robustness": {"type": "number"},
                    "generalization": {"type": "number"},
                    "efficiency": {"type": "number"},
                    "weighted_score": {"type": "number"},
                    "critical_gate_failed": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
        },
        "weights": {
            "type": "object",
            "required": ["physics", "real_data", "extreme_events", "robustness", "generalization", "efficiency"],
            "properties": {
                "physics": {"type": "number"},
                "real_data": {"type": "number"},
                "extreme_events": {"type": "number"},
                "robustness": {"type": "number"},
                "generalization": {"type": "number"},
                "efficiency": {"type": "number"},
            },
            "additionalProperties": False,
        },
        "canonical_simulator": {"type": "string"},
        "selection_status": {"type": "string"},
        "selection_method": {"type": "string"},
        "critical_gates": {
            "type": "object",
            "additionalProperties": {"type": "string"},
        },
    },
    "additionalProperties": False,
}


def get_schema(name: str) -> Dict[str, Any]:
    """Return a copy of the requested schema.

    Currently only ``"simulator_metrics"`` is supported.
    """
    if name == "simulator_metrics":
        return SIMULATOR_METRICS_SCHEMA.copy()
    raise KeyError(f"Unknown schema: {name}")


__all__ = ["SIMULATOR_METRICS_SCHEMA", "get_schema"]
