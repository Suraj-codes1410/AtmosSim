"""
Puff Lifecycle Management Module for AtmosSim Gaussian Puff Engine.

Defines lifecycle state transitions (CREATED -> ACTIVE -> CULLED),
configurable multi-criteria computational domain culling policies (age, distance, mass, spatial bounds),
and memory boundedness monitoring.

Note on Culling Semantics
-------------------------
Puff culling is a COMPUTATIONAL / DOMAIN MANAGEMENT technique to keep active memory and evaluation
runtime strictly bounded within the region of interest. It is not a physical removal process (unless
exponential physical decay or surface deposition is explicitly configured).

References
----------
1. Scire, J. S., Strimaitis, D. G., & Yamartino, R. J. (2000). A User's Guide for the
   CALPUFF Dispersion Model. Earth Tech, Inc., Concord, MA. (Section 2.1: Puff Lifecycle).
2. Zannetti, P. (1990). Air Pollution Modeling: Theories, Computational Methods and Available
   Software. Computational Mechanics Publications / Van Nostrand Reinhold. Chapter 6.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple
import math
import numpy as np


class PuffLifecycleState(str, Enum):
    """Lifecycle state of an atmospheric puff parcel."""
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    CULLED = "CULLED"


class PuffCullReason(str, Enum):
    """Specific cause for puff deactivation and memory culling."""
    NONE = "NONE"
    MAX_AGE = "MAX_AGE"
    MAX_DISTANCE = "MAX_DISTANCE"
    MIN_MASS = "MIN_MASS"
    DOMAIN_BOUNDS = "DOMAIN_BOUNDS"


@dataclass(frozen=True)
class SpatialBounds:
    """
    3D spatial bounding box for the active computational domain (in meters).
    """
    x_min: float = -100000.0
    x_max: float = 100000.0
    y_min: float = -100000.0
    y_max: float = 100000.0
    z_min: float = 0.0
    z_max: float = 10000.0

    def contains(self, x: float, y: float, z: float) -> bool:
        """Check whether point (x, y, z) lies within the bounding box."""
        return (
            self.x_min <= x <= self.x_max
            and self.y_min <= y <= self.y_max
            and self.z_min <= z <= self.z_max
        )


@dataclass(frozen=True)
class PuffLifecycleConfig:
    """
    Configuration parameters governing puff deactivation and computational bounds.

    Parameters
    ----------
    max_age : float, default=7200.0
        Maximum active puff age in seconds (e.g. 7200s = 2 hours). Puffs older than
        this threshold are culled.
    max_distance : float, default=50000.0
        Maximum radial distance in meters from source origin (e.g. 50 km).
    min_mass : float, default=1e-8
        Minimum pollutant mass in grams. Puffs depleted below this mass threshold are culled.
    bounds : Optional[SpatialBounds], optional
        Spatial computational bounding box. Puffs moving outside are culled.
    """
    max_age: float = 7200.0
    max_distance: float = 50000.0
    min_mass: float = 1e-8
    bounds: Optional[SpatialBounds] = None

    def __post_init__(self):
        if self.max_age <= 0.0:
            raise ValueError(f"max_age must be strictly positive, got {self.max_age}")
        if self.max_distance <= 0.0:
            raise ValueError(f"max_distance must be strictly positive, got {self.max_distance}")
        if self.min_mass < 0.0:
            raise ValueError(f"min_mass must be non-negative, got {self.min_mass}")


@dataclass
class PuffLifecycleStats:
    """Diagnostic accounting metrics tracking puff population dynamics."""
    created_count: int = 0
    active_count: int = 0
    culled_count: int = 0
    peak_active_count: int = 0
    cull_reasons: dict = field(default_factory=lambda: {r.value: 0 for r in PuffCullReason if r != PuffCullReason.NONE})

    def record_creation(self, count: int = 1) -> None:
        self.created_count += count
        self.active_count += count
        if self.active_count > self.peak_active_count:
            self.peak_active_count = self.active_count

    def record_cull(self, reason: PuffCullReason, count: int = 1) -> None:
        self.active_count -= count
        self.culled_count += count
        if reason.value in self.cull_reasons:
            self.cull_reasons[reason.value] += count


def evaluate_cull_condition(
    age: float,
    x: float,
    y: float,
    z: float,
    mass: float,
    source_x: float,
    source_y: float,
    config: PuffLifecycleConfig,
) -> Tuple[bool, PuffCullReason]:
    """
    Determine whether a puff should be culled according to configured lifecycle policies.

    Parameters
    ----------
    age : float
        Current puff age in seconds (t - t_release).
    x, y, z : float
        Current 3D Cartesian coordinates of puff center in meters.
    mass : float
        Current mass of pollutant in the puff (g).
    source_x, source_y : float
        Origin coordinates of emission source in meters.
    config : PuffLifecycleConfig
        Culling rules configuration.

    Returns
    -------
    Tuple[bool, PuffCullReason]
        (should_cull, reason)
    """
    # 1. Age threshold
    if age > config.max_age:
        return True, PuffCullReason.MAX_AGE

    # 2. Distance threshold
    dist = math.hypot(x - source_x, y - source_y)
    if dist > config.max_distance:
        return True, PuffCullReason.MAX_DISTANCE

    # 3. Minimum mass threshold
    if mass < config.min_mass:
        return True, PuffCullReason.MIN_MASS

    # 4. Spatial bounding box
    if config.bounds is not None and not config.bounds.contains(x, y, z):
        return True, PuffCullReason.DOMAIN_BOUNDS

    return False, PuffCullReason.NONE
