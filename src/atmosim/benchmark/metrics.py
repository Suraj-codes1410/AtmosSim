# -*- coding: utf-8 -*-
"""Benchmark metrics definitions.

Only lightweight data containers are defined here.  Real computation lives in
``benchmark.comparison``; this module merely provides typed results that are used
by the selection logic and by the JSON schema in ``benchmark.schemas``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


# Continuous (field‑wise) metrics ------------------------------------------------
@dataclass(frozen=True)
class ContinuousMetrics:
    mae: float
    rmse: float
    mean_bias: float
    normalized_mean_bias: float
    correlation: float
    r_squared: float
    normalized_rmse: Optional[float] = None


# Event‑based metrics -----------------------------------------------------------
@dataclass(frozen=True)
class EventMetrics:
    peak_observed: float
    peak_modeled: float
    peak_bias: float
    peak_ratio: float
    peak_time_observed: float  # hours since start
    peak_time_modeled: float
    peak_timing_error: float
    precision: float
    recall: float
    f1: float


# Spatial metrics ---------------------------------------------------------------
@dataclass(frozen=True)
class SpatialMetrics:
    spatial_mae: float
    spatial_rmse: float
    spatial_bias: float
    spatial_correlation: float


# Seasonal aggregation ----------------------------------------------------------
@dataclass(frozen=True)
class SeasonalMetrics:
    season: str
    metrics: ContinuousMetrics


# Robustness & generalization ---------------------------------------------------
@dataclass(frozen=True)
class RobustnessMetrics:
    numeric_stability: bool
    perturbation_sensitivity: float  # relative change
    failure_rate: float


@dataclass(frozen=True)
class GeneralizationMetrics:
    temporal_generalization: float
    seasonal_generalization: float
    spatial_generalization: float
    regime_generalization: float


# Efficiency -------------------------------------------------------------------
@dataclass(frozen=True)
class EfficiencyMetrics:
    wall_clock_seconds: float
    cpu_seconds: Optional[float] = None
    memory_mb: Optional[float] = None
    num_puffs: Optional[int] = None
    num_receptors: Optional[int] = None


# Aggregated result for a single candidate --------------------------------------
@dataclass(frozen=True)
class CandidateMetrics:
    continuous: ContinuousMetrics
    event: EventMetrics
    spatial: SpatialMetrics
    seasonal: List[SeasonalMetrics]
    robustness: RobustnessMetrics
    generalization: GeneralizationMetrics
    efficiency: EfficiencyMetrics


__all__ = [
    "ContinuousMetrics",
    "EventMetrics",
    "SpatialMetrics",
    "SeasonalMetrics",
    "RobustnessMetrics",
    "GeneralizationMetrics",
    "EfficiencyMetrics",
    "CandidateMetrics",
]
