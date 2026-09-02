# -*- coding: utf-8 -*-
"""Benchmark selection utilities.

The selection layer implements the reproducible weighted‑score algorithm
required by Phase 4/5. It operates on a mapping of candidate names to a
dictionary containing the six category scores (already normalized to the
0‑100 range) and the pre‑computed ``weighted_score``. The public API is:

* ``compute_weighted_score(scores: dict, weights: dict | None = None) -> float`` –
  multiply each category by its weight and sum.
* ``apply_scientific_gates(candidate_data: dict) -> dict`` – remove candidates that
  have a ``critical_gate_failed`` flag set to ``True``.
* ``deterministic_tie_breaker(candidates: list[str], scores: dict) -> str`` –
  break ties using the ordered preference list defined by the specification.
* ``select_canonical_simulator(candidate_scores: dict) -> str`` – combine the
  steps above and return the winning candidate name.
"""

from __future__ import annotations

from typing import Dict, List

# Default weight distribution (must sum to 1.0)
DEFAULT_WEIGHTS: Dict[str, float] = {
    "physics": 0.20,
    "real_data": 0.30,
    "extreme_events": 0.20,
    "robustness": 0.10,
    "generalization": 0.10,
    "efficiency": 0.10,
}

# Preference order for deterministic tie‑breaking (high‑level priority)
TIE_BREAK_ORDER: List[str] = [
    "real_data",
    "extreme_events",
    "physics",
    "efficiency",
]


def compute_weighted_score(category_scores: Dict[str, float], weights: Dict[str, float] | None = None) -> float:
    """Return the weighted sum of normalized category scores.

    Parameters
    ----------
    category_scores: dict
        Mapping from category name (e.g. ``"physics"``) to a score in the
        ``0‑100`` range.
    weights: dict, optional
        Custom weight mapping; if ``None`` the ``DEFAULT_WEIGHTS`` are used.
    """
    w = weights if weights is not None else DEFAULT_WEIGHTS
    return sum(category_scores.get(cat, 0.0) * w.get(cat, 0.0) for cat in w)


def apply_scientific_gates(candidate_data: Dict[str, dict]) -> Dict[str, dict]:
    """Filter out candidates that failed a critical scientific gate.

    The input mapping uses the candidate name as the key and a dictionary of
    scores as the value. If a candidate dictionary contains the key
    ``"critical_gate_failed"`` with a truthy value it is removed from the
    returned mapping.
    """
    return {name: data for name, data in candidate_data.items() if not data.get("critical_gate_failed")}


def deterministic_tie_breaker(candidates: List[str], scores: Dict[str, dict]) -> str:
    """Break ties deterministically according to the specification.

    The ``candidates`` list contains the names of the tied candidates. The
    function iterates over ``TIE_BREAK_ORDER`` and selects the candidate with the
    highest score for the current category. If the tie persists after all tie‑
    break categories are examined, the function returns the alphabetically first
    name (ensuring a stable deterministic outcome).
    """
    if len(candidates) == 1:
        return candidates[0]

    remaining = set(candidates)
    for cat in TIE_BREAK_ORDER:
        max_score = max(scores[name].get(cat, 0.0) for name in remaining)
        remaining = {name for name in remaining if scores[name].get(cat, 0.0) == max_score}
        if len(remaining) == 1:
            return next(iter(remaining))
    return sorted(remaining)[0]


def select_canonical_simulator(candidate_scores: Dict[str, dict]) -> str:
    """Select the canonical simulator according to weighted score and gates.

    Steps performed:
    1. Apply scientific gates – candidates with ``critical_gate_failed=True``
       are excluded.
    2. Compute the weighted score for each remaining candidate (if not already
       present under the key ``"weighted_score"``).
    3. Identify the highest weighted score.
    4. If more than one candidate shares the top score, apply the deterministic
       tie‑breaker.
    """
    filtered = apply_scientific_gates(candidate_scores)
    if not filtered:
        raise ValueError("All candidates were filtered out by scientific gates.")

    for name, data in filtered.items():
        if "weighted_score" not in data:
            data["weighted_score"] = compute_weighted_score(data, DEFAULT_WEIGHTS)

    top_score = max(d["weighted_score"] for d in filtered.values())
    top_candidates = [name for name, d in filtered.items() if d["weighted_score"] == top_score]

    return deterministic_tie_breaker(top_candidates, filtered)


__all__ = [
    "DEFAULT_WEIGHTS",
    "TIE_BREAK_ORDER",
    "compute_weighted_score",
    "apply_scientific_gates",
    "deterministic_tie_breaker",
    "select_canonical_simulator",
]
