# -*- coding: utf-8 -*-
"""Tests for benchmark selection utilities.

These tests verify deterministic tie‑breaking, weighted‑score calculation and
scientific‑gate handling without requiring any heavy simulation data.
"""

from atmosim.benchmark.selection import (
    compute_weighted_score,
    apply_scientific_gates,
    deterministic_tie_breaker,
    select_canonical_simulator,
    DEFAULT_WEIGHTS,
)


def test_compute_weighted_score_default_weights():
    scores = {
        "physics": 80,
        "real_data": 70,
        "extreme_events": 60,
        "robustness": 90,
        "generalization": 85,
        "efficiency": 75,
    }
    weighted = compute_weighted_score(scores)
    expected = (
        80 * 0.20
        + 70 * 0.30
        + 60 * 0.20
        + 90 * 0.10
        + 85 * 0.10
        + 75 * 0.10
    )
    assert abs(weighted - expected) < 1e-6


def test_apply_scientific_gates_filters():
    data = {
        "plume": {"physics": 80, "critical_gate_failed": False},
        "puff": {"physics": 85, "critical_gate_failed": True},
    }
    filtered = apply_scientific_gates(data)
    assert "plume" in filtered
    assert "puff" not in filtered


def test_deterministic_tie_breaker():
    candidates = ["plume", "puff", "hysplit"]
    scores = {
        "plume": {"real_data": 70, "extreme_events": 60, "physics": 80, "efficiency": 90},
        "puff": {"real_data": 70, "extreme_events": 65, "physics": 80, "efficiency": 85},
        "hysplit": {"real_data": 70, "extreme_events": 65, "physics": 80, "efficiency": 88},
    }
    winner = deterministic_tie_breaker(candidates, scores)
    # real_data equal, extreme_events highest for puff and hysplit (65)
    # physics equal, then efficiency decides: hysplit 88 > puff 85 > plume 90? plume excluded after previous step.
    assert winner == "hysplit"


def test_select_canonical_simulator_full_flow():
    data = {
        "plume": {
            "physics": 80,
            "real_data": 70,
            "extreme_events": 60,
            "robustness": 90,
            "generalization": 85,
            "efficiency": 75,
        },
        "puff": {
            "physics": 85,
            "real_data": 70,
            "extreme_events": 60,
            "robustness": 90,
            "generalization": 85,
            "efficiency": 75,
            "critical_gate_failed": True,
        },
    }
    winner = select_canonical_simulator(data)
    assert winner == "plume"
