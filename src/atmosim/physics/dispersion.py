"""
Atmospheric dispersion coefficients module for AtmosSim.

Implements the Briggs (1973, 1974) dispersion parameterizations for horizontal (sigma_y)
and vertical (sigma_z) plume spread as functions of downwind distance x and Pasquill-Gifford
stability classes (A through F) for both Rural and Urban environments.

References
----------
1. Briggs, G. A. (1973). Diffusion Estimation for Small Emissions.
   ATDL Report No. 79, Atmospheric Turbulence and Diffusion Laboratory,
   National Oceanic and Atmospheric Administration (NOAA), Oak Ridge, TN.
2. Briggs, G. A. (1974). Diffusion Estimation for Small Emissions.
   In: USAEC Report TID-26712, pp. 83-145.
3. Gifford, F. A. (1976). Turbulent diffusion-typing schemes: A review.
   Nuclear Safety, 17(1), 68-86.
4. U.S. EPA (1995). User's Guide for the Industrial Source Complex (ISC3) Dispersion
   Models: Volume II - Description of Model Algorithms. EPA-454/B-95-003b.
"""

from enum import Enum
from typing import Tuple, Union
import numpy as np

from atmosim.physics.stability import StabilityClass


class EnvironmentType(str, Enum):
    """Terrain / surface roughness environment type for dispersion formulas."""
    RURAL = "RURAL"
    URBAN = "URBAN"


# Valid empirical calibration range for Briggs dispersion formulas (in meters)
# Field experiments (Prairie Grass, Round Hill, etc.) had measurement arcs primarily in this range.
BRIGGS_MIN_X: float = 100.0       # 100 meters (0.1 km)
BRIGGS_MAX_X: float = 10000.0     # 10,000 meters (10.0 km)


def is_in_briggs_empirical_range(x: Union[float, int, np.ndarray]) -> Union[bool, np.ndarray]:
    """
    Check whether downwind distance(s) lie within the empirically calibrated Briggs range [100m, 10000m].

    Parameters
    ----------
    x : float, int, or np.ndarray
        Downwind distance in meters.

    Returns
    -------
    bool or np.ndarray
        True if 100.0 <= x <= 10000.0, False otherwise.
    """
    is_scalar = np.isscalar(x)
    x_arr = np.asanyarray(x, dtype=np.float64)
    in_range = (x_arr >= BRIGGS_MIN_X) & (x_arr <= BRIGGS_MAX_X)
    return bool(in_range) if is_scalar else in_range


def _validate_distance(x: Union[float, int, np.ndarray]) -> np.ndarray:
    """
    Validate downwind distance input. Must be strictly positive and finite.

    Parameters
    ----------
    x : float, int, or np.ndarray
        Downwind distance in meters.

    Returns
    -------
    np.ndarray
        Validated floating-point array of distances.

    Raises
    ------
    ValueError
        If any distance value is <= 0, NaN, or infinite.
    """
    x_arr = np.asanyarray(x, dtype=np.float64)

    if not np.all(np.isfinite(x_arr)):
        raise ValueError("Downwind distance 'x' contains NaN or infinite values.")

    if np.any(x_arr <= 0.0):
        raise ValueError(
            "Downwind distance 'x' must be strictly positive (x > 0 m). "
            "Dispersion coefficients are undefined for x <= 0."
        )

    return x_arr


def compute_sigma_y(
    x: Union[float, int, np.ndarray],
    stability: Union[StabilityClass, str],
    environment: Union[EnvironmentType, str] = EnvironmentType.RURAL,
) -> Union[float, np.ndarray]:
    """
    Calculate the crosswind horizontal dispersion coefficient sigma_y(x) in meters.

    Parameters
    ----------
    x : float or np.ndarray
        Downwind distance along plume axis in meters (x > 0).
    stability : StabilityClass or str
        Pasquill-Gifford stability class (A, B, C, D, E, or F).
    environment : EnvironmentType or str, default=RURAL
        Environment surface classification (RURAL or URBAN).

    Returns
    -------
    float or np.ndarray
        sigma_y in meters. Output matches input scalar/array format.

    References
    ----------
    Briggs (1973), EPA ISC3 Model Description (1995, Section 1.1.2).
    """
    is_scalar = np.isscalar(x)
    x_arr = _validate_distance(x)
    st = StabilityClass(stability) if isinstance(stability, str) else stability
    env = EnvironmentType(environment) if isinstance(environment, str) else environment

    if env == EnvironmentType.RURAL:
        # Rural Briggs sigma_y formula:
        # sigma_y = a * x / sqrt(1 + 0.0001 * x)
        rural_a = {
            StabilityClass.A: 0.22,
            StabilityClass.B: 0.16,
            StabilityClass.C: 0.11,
            StabilityClass.D: 0.08,
            StabilityClass.E: 0.06,
            StabilityClass.F: 0.04,
        }
        a = rural_a[st]
        sigma_y = (a * x_arr) / np.sqrt(1.0 + 0.0001 * x_arr)

    elif env == EnvironmentType.URBAN:
        # Urban Briggs (McElroy-Pooler) sigma_y formula:
        # sigma_y = a * x / sqrt(1 + 0.0004 * x)
        urban_a = {
            StabilityClass.A: 0.32,
            StabilityClass.B: 0.32,
            StabilityClass.C: 0.22,
            StabilityClass.D: 0.16,
            StabilityClass.E: 0.11,
            StabilityClass.F: 0.11,
        }
        a = urban_a[st]
        sigma_y = (a * x_arr) / np.sqrt(1.0 + 0.0004 * x_arr)
    else:
        raise ValueError(f"Unknown environment type: {environment}")

    return float(sigma_y) if is_scalar else sigma_y


def compute_sigma_z(
    x: Union[float, int, np.ndarray],
    stability: Union[StabilityClass, str],
    environment: Union[EnvironmentType, str] = EnvironmentType.RURAL,
) -> Union[float, np.ndarray]:
    """
    Calculate the vertical dispersion coefficient sigma_z(x) in meters.

    Parameters
    ----------
    x : float or np.ndarray
        Downwind distance along plume axis in meters (x > 0).
    stability : StabilityClass or str
        Pasquill-Gifford stability class (A, B, C, D, E, or F).
    environment : EnvironmentType or str, default=RURAL
        Environment surface classification (RURAL or URBAN).

    Returns
    -------
    float or np.ndarray
        sigma_z in meters. Output matches input scalar/array format.

    References
    ----------
    Briggs (1973), EPA ISC3 Model Description (1995, Section 1.1.2).
    """
    is_scalar = np.isscalar(x)
    x_arr = _validate_distance(x)
    st = StabilityClass(stability) if isinstance(stability, str) else stability
    env = EnvironmentType(environment) if isinstance(environment, str) else environment

    if env == EnvironmentType.RURAL:
        if st == StabilityClass.A:
            sigma_z = 0.20 * x_arr
        elif st == StabilityClass.B:
            sigma_z = 0.12 * x_arr
        elif st == StabilityClass.C:
            sigma_z = (0.08 * x_arr) / np.sqrt(1.0 + 0.0002 * x_arr)
        elif st == StabilityClass.D:
            sigma_z = (0.06 * x_arr) / np.sqrt(1.0 + 0.0015 * x_arr)
        elif st == StabilityClass.E:
            sigma_z = (0.03 * x_arr) / (1.0 + 0.0003 * x_arr)
        elif st == StabilityClass.F:
            sigma_z = (0.016 * x_arr) / (1.0 + 0.0003 * x_arr)
        else:
            raise ValueError(f"Unknown stability class: {st}")

    elif env == EnvironmentType.URBAN:
        if st in (StabilityClass.A, StabilityClass.B):
            sigma_z = 0.24 * x_arr * np.sqrt(1.0 + 0.001 * x_arr)
        elif st == StabilityClass.C:
            sigma_z = 0.20 * x_arr
        elif st == StabilityClass.D:
            sigma_z = (0.14 * x_arr) / np.sqrt(1.0 + 0.0003 * x_arr)
        elif st in (StabilityClass.E, StabilityClass.F):
            sigma_z = (0.08 * x_arr) / np.sqrt(1.0 + 0.0015 * x_arr)
        else:
            raise ValueError(f"Unknown stability class: {st}")
    else:
        raise ValueError(f"Unknown environment type: {environment}")

    return float(sigma_z) if is_scalar else sigma_z


def compute_dispersion_coefficients(
    x: Union[float, int, np.ndarray],
    stability: Union[StabilityClass, str],
    environment: Union[EnvironmentType, str] = EnvironmentType.RURAL,
) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
    """
    Calculate both sigma_y and sigma_z simultaneously for given downwind distance(s).

    Parameters
    ----------
    x : float or np.ndarray
        Downwind distance in meters (x > 0).
    stability : StabilityClass or str
        Pasquill-Gifford stability class (A through F).
    environment : EnvironmentType or str, default=RURAL
        RURAL or URBAN parameterization.

    Returns
    -------
    Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]
        (sigma_y, sigma_z) in meters.
    """
    sy = compute_sigma_y(x, stability=stability, environment=environment)
    sz = compute_sigma_z(x, stability=stability, environment=environment)
    return sy, sz
