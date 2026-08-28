"""
Analytical steady-state Gaussian Plume dispersion model for AtmosSim.

Implements the standard steady-state Gaussian plume equation with ground reflection,
supporting both decoupled dispersion coefficients and integrated Briggs/PG stability calculations.

Governing Equation
------------------
For a continuous point source at (0, 0, H) with uniform wind speed u along the positive x-axis:

C(x, y, z) = [ Q / (2 * pi * u * sigma_y * sigma_z) ]
             * exp( - y^2 / (2 * sigma_y^2) )
             * [ exp( - (z - H)^2 / (2 * sigma_z^2) ) + exp( - (z + H)^2 / (2 * sigma_z^2) ) ]

References
----------
1. Turner, D. B. (1970). Workbook of Atmospheric Dispersion Estimates.
   U.S. EPA Office of Air Programs Publication No. AP-26.
2. Seinfeld, J. H., & Pandis, S. N. (2016). Atmospheric Chemistry and Physics:
   From Air Pollution to Climate Change (3rd ed.). John Wiley & Sons. Chapter 18, Eq. 18.39-18.44.
3. Sutton, O. G. (1932). A theory of eddy diffusion in the atmosphere.
   Proceedings of the Royal Society of London. Series A, 135(828), 143-165.
4. Pasquill, F. (1961). The estimation of the dispersion of windborne material.
   The Meteorological Magazine, 90(1063), 33-49.
"""

from typing import Optional, Tuple, Union
import numpy as np

from atmosim.physics.stability import StabilityClass
from atmosim.physics.dispersion import (
    EnvironmentType,
    compute_sigma_y,
    compute_sigma_z,
    compute_dispersion_coefficients,
)


def _validate_plume_inputs(
    Q: float,
    wind_speed: float,
    effective_height: float,
    z: Union[float, np.ndarray],
    sigma_y: Union[float, np.ndarray],
    sigma_z: Union[float, np.ndarray],
) -> None:
    """Validate physical parameters for Gaussian plume computation."""
    # Emission rate
    if not np.isfinite(Q) or Q < 0.0:
        raise ValueError(f"Emission rate Q must be a non-negative finite number, got {Q}")

    # Wind speed
    if not np.isfinite(wind_speed) or wind_speed <= 0.0:
        raise ValueError(
            f"Wind speed u must be strictly positive and finite (u > 0 m/s), got {wind_speed}"
        )

    # Effective height
    if not np.isfinite(effective_height) or effective_height < 0.0:
        raise ValueError(
            f"Effective source height H must be non-negative and finite (H >= 0 m), got {effective_height}"
        )

    # Receptor height
    z_arr = np.asanyarray(z)
    if not np.all(np.isfinite(z_arr)):
        raise ValueError("Receptor height z contains NaN or infinite values.")
    if np.any(z_arr < 0.0):
        raise ValueError("Receptor height z must be non-negative (z >= 0 m).")

    # Dispersion coefficients
    sy_arr = np.asanyarray(sigma_y)
    sz_arr = np.asanyarray(sigma_z)
    if not np.all(np.isfinite(sy_arr)) or not np.all(np.isfinite(sz_arr)):
        raise ValueError("Dispersion coefficients sigma_y / sigma_z contain NaN or infinite values.")
    if np.any(sy_arr <= 0.0) or np.any(sz_arr <= 0.0):
        raise ValueError("Dispersion coefficients sigma_y and sigma_z must be strictly positive (sigma > 0 m).")


def gaussian_plume_concentration(
    y: Union[float, np.ndarray],
    z: Union[float, np.ndarray],
    Q: float,
    wind_speed: float,
    effective_height: float,
    sigma_y: Union[float, np.ndarray],
    sigma_z: Union[float, np.ndarray],
    include_ground_reflection: bool = True,
) -> Union[float, np.ndarray]:
    """
    Compute steady-state Gaussian plume concentration C(y, z) given dispersion widths.

    Parameters
    ----------
    y : float or np.ndarray
        Crosswind horizontal coordinate in meters (y = 0 at plume centerline).
    z : float or np.ndarray
        Receptor vertical height above ground in meters (z >= 0).
    Q : float
        Emission mass rate in mass/s (e.g. g/s or kg/s). Must be >= 0.
    wind_speed : float
        Mean horizontal advection wind speed in m/s at release height (u > 0).
    effective_height : float
        Effective source release height H in meters (H >= 0).
    sigma_y : float or np.ndarray
        Horizontal crosswind dispersion standard deviation in meters (sigma_y > 0).
    sigma_z : float or np.ndarray
        Vertical dispersion standard deviation in meters (sigma_z > 0).
    include_ground_reflection : bool, default=True
        Whether to include the method-of-images ground reflection term exp(-(z+H)^2/(2*sigma_z^2)).

    Returns
    -------
    float or np.ndarray
        Simulated mass concentration in mass/m³ (matching unit numerator of Q).
        Returns scalar if all inputs are scalar, or NumPy ndarray matching broadcast shape.

    Notes
    -----
    The formulation assumes steady-state, continuous emission, uniform horizontal advection
    along positive x, horizontally homogeneous turbulence, and perfect reflection at the surface (z=0).
    """
    _validate_plume_inputs(
        Q=Q,
        wind_speed=wind_speed,
        effective_height=effective_height,
        z=z,
        sigma_y=sigma_y,
        sigma_z=sigma_z,
    )

    is_all_scalar = (
        np.isscalar(y) and np.isscalar(z) and np.isscalar(sigma_y) and np.isscalar(sigma_z)
    )

    y_arr = np.asanyarray(y, dtype=np.float64)
    z_arr = np.asanyarray(z, dtype=np.float64)
    sy_arr = np.asanyarray(sigma_y, dtype=np.float64)
    sz_arr = np.asanyarray(sigma_z, dtype=np.float64)

    if not np.all(np.isfinite(y_arr)):
        raise ValueError("Crosswind coordinate y contains NaN or infinite values.")

    # Prefactor: Q / (2 * pi * u * sigma_y * sigma_z)
    prefactor = Q / (2.0 * np.pi * wind_speed * sy_arr * sz_arr)

    # Crosswind Gaussian component: exp(- y^2 / (2 * sigma_y^2))
    crosswind_term = np.exp(-0.5 * (y_arr / sy_arr) ** 2)

    # Direct vertical term: exp(- (z - H)^2 / (2 * sigma_z^2))
    direct_vertical = np.exp(-0.5 * ((z_arr - effective_height) / sz_arr) ** 2)

    if include_ground_reflection:
        # Reflected vertical term: exp(- (z + H)^2 / (2 * sigma_z^2))
        reflected_vertical = np.exp(-0.5 * ((z_arr + effective_height) / sz_arr) ** 2)
        vertical_term = direct_vertical + reflected_vertical
    else:
        vertical_term = direct_vertical

    # Total concentration field
    conc = prefactor * crosswind_term * vertical_term

    return float(conc) if is_all_scalar else conc


class GaussianPlumeModel:
    """
    Configured steady-state Gaussian Plume dispersion model.

    Encapsulates source emissions, meteorological advection, stability classification,
    and terrain roughness parameterization to evaluate concentrations on arbitrary spatial coordinates.
    """

    def __init__(
        self,
        Q: float,
        wind_speed: float,
        effective_height: float,
        stability: Union[StabilityClass, str],
        environment: Union[EnvironmentType, str] = EnvironmentType.RURAL,
        include_ground_reflection: bool = True,
    ) -> None:
        """
        Initialize the Gaussian Plume model.

        Parameters
        ----------
        Q : float
            Emission rate in mass/s (e.g. g/s, kg/s). Must be >= 0.
        wind_speed : float
            Mean horizontal wind speed in m/s (u > 0).
        effective_height : float
            Effective source release height H in meters (H >= 0).
        stability : StabilityClass or str
            Pasquill-Gifford stability class (A, B, C, D, E, or F).
        environment : EnvironmentType or str, default=RURAL
            Atmospheric surface roughness environment (RURAL or URBAN).
        include_ground_reflection : bool, default=True
            Include ground reflection term (method of images).
        """
        if not np.isfinite(Q) or Q < 0.0:
            raise ValueError(f"Emission rate Q must be non-negative and finite, got {Q}")
        if not np.isfinite(wind_speed) or wind_speed <= 0.0:
            raise ValueError(f"Wind speed u must be strictly positive and finite (u > 0 m/s), got {wind_speed}")
        if not np.isfinite(effective_height) or effective_height < 0.0:
            raise ValueError(f"Effective height H must be non-negative and finite (H >= 0 m), got {effective_height}")

        self.Q = float(Q)
        self.wind_speed = float(wind_speed)
        self.effective_height = float(effective_height)
        self.stability = StabilityClass(stability) if isinstance(stability, str) else stability
        self.environment = EnvironmentType(environment) if isinstance(environment, str) else environment
        self.include_ground_reflection = bool(include_ground_reflection)

    def compute_sigmas(
        self,
        x: Union[float, int, np.ndarray],
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        """Compute (sigma_y, sigma_z) at downwind distance(s) x using the model's stability & environment."""
        return compute_dispersion_coefficients(
            x=x,
            stability=self.stability,
            environment=self.environment,
        )

    def evaluate(
        self,
        x: Union[float, int, np.ndarray],
        y: Union[float, int, np.ndarray],
        z: Union[float, int, np.ndarray] = 0.0,
    ) -> Union[float, np.ndarray]:
        """
        Evaluate steady-state mass concentration at coordinates (x, y, z).

        Parameters
        ----------
        x : float or np.ndarray
            Downwind distance in meters along the plume axis (x > 0).
        y : float or np.ndarray
            Crosswind horizontal coordinate in meters (centerline at y = 0).
        z : float or np.ndarray, default=0.0
            Receptor vertical height in meters above ground (z >= 0).

        Returns
        -------
        float or np.ndarray
            Concentration in mass/m³.
        """
        # Compute dispersion coefficients at downwind coordinate(s) x
        sigma_y, sigma_z = self.compute_sigmas(x)

        return gaussian_plume_concentration(
            y=y,
            z=z,
            Q=self.Q,
            wind_speed=self.wind_speed,
            effective_height=self.effective_height,
            sigma_y=sigma_y,
            sigma_z=sigma_z,
            include_ground_reflection=self.include_ground_reflection,
        )
