"""
Physics module for AtmosSim.
Contains analytical and empirical implementations for atmospheric stability,
dispersion coefficients, steady-state Gaussian plume, and time-dependent Gaussian puff engines.
"""

from atmosim.physics.stability import StabilityClass, classify_stability
from atmosim.physics.dispersion import (
    EnvironmentType,
    BRIGGS_MIN_X,
    BRIGGS_MAX_X,
    is_in_briggs_empirical_range,
    compute_sigma_y,
    compute_sigma_z,
    compute_dispersion_coefficients,
)
from atmosim.physics.plume import (
    gaussian_plume_concentration,
    GaussianPlumeModel,
)
from atmosim.physics.coordinates import (
    LocalCoordinateSystem,
    determine_utm_epsg,
)
from atmosim.physics.puff_lifecycle import (
    PuffLifecycleConfig,
    PuffLifecycleState,
    PuffCullReason,
    PuffLifecycleStats,
    SpatialBounds,
    evaluate_cull_condition,
)
from atmosim.physics.puff import (
    EmissionSource,
    GaussianPuff,
    GaussianPuffConfig,
    GaussianPuffEngine,
    WindField,
    evaluate_single_puff_concentration,
    meteorological_wind_to_cartesian,
    cartesian_wind_to_meteorological,
)

__all__ = [
    "StabilityClass",
    "classify_stability",
    "EnvironmentType",
    "BRIGGS_MIN_X",
    "BRIGGS_MAX_X",
    "is_in_briggs_empirical_range",
    "compute_sigma_y",
    "compute_sigma_z",
    "compute_dispersion_coefficients",
    "gaussian_plume_concentration",
    "GaussianPlumeModel",
    "LocalCoordinateSystem",
    "determine_utm_epsg",
    "PuffLifecycleConfig",
    "PuffLifecycleState",
    "PuffCullReason",
    "PuffLifecycleStats",
    "SpatialBounds",
    "evaluate_cull_condition",
    "EmissionSource",
    "GaussianPuff",
    "GaussianPuffConfig",
    "GaussianPuffEngine",
    "WindField",
    "evaluate_single_puff_concentration",
    "meteorological_wind_to_cartesian",
    "cartesian_wind_to_meteorological",
]
