# -*- coding: utf-8 -*-
"""Benchmark package for AtmosSim.

This package provides utilities to run controlled benchmark scenarios,
compare candidate simulators, compute metrics, and select a canonical
simulator based on a reproducible multi‑criteria scoring framework.

The implementation deliberately isolates benchmark logic from the core
physics engine so that frozen Phase 0‑2 code remains unchanged.
"""

__all__ = [
    "scenarios",
    "runner",
    "metrics",
    "comparison",
    "selection",
    "schemas",
]
