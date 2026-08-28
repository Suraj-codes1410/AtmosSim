"""
Atmospheric stability classification module for AtmosSim.

Implements the Pasquill-Gifford-Turner (PGT) atmospheric stability classification
framework based on surface wind speed, daytime insolation (solar radiation / solar elevation),
and nighttime cloud cover.

References
----------
1. Pasquill, F. (1961). The estimation of the dispersion of windborne material.
   The Meteorological Magazine, 90(1063), 33-49.
2. Gifford, F. A. (1961). Use of routine meteorological observations for estimating
   atmospheric dispersion. Nuclear Safety, 2(4), 47-51.
3. Turner, D. B. (1964). A diffusion model for an urban area.
   Journal of Applied Meteorology, 3(1), 83-91.
4. U.S. EPA (1995). User's Guide for the Industrial Source Complex (ISC3) Dispersion
   Models: Volume II - Description of Model Algorithms. EPA-454/B-95-003b.
   U.S. Environmental Protection Agency, Research Triangle Park, NC.
"""

from enum import Enum
from typing import Optional, Union
import math


class StabilityClass(str, Enum):
    """
    Pasquill-Gifford atmospheric stability classes (A through F).

    A: Extremely unstable (strong daytime solar heating, convective mixing)
    B: Moderately unstable
    C: Slightly unstable
    D: Neutral (high winds, overcast skies, or transition periods)
    E: Slightly stable (nighttime, moderate cloudiness, weak radiative cooling)
    F: Moderately/Extremely stable (clear nighttime, light winds, strong radiative inversion)
    """
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"

    def __str__(self) -> str:
        return self.value

    @property
    def description(self) -> str:
        """Human-readable description of the stability class."""
        descriptions = {
            StabilityClass.A: "Extremely unstable",
            StabilityClass.B: "Moderately unstable",
            StabilityClass.C: "Slightly unstable",
            StabilityClass.D: "Neutral",
            StabilityClass.E: "Slightly stable",
            StabilityClass.F: "Moderately/Extremely stable",
        }
        return descriptions[self]


class InsolationCategory(str, Enum):
    """Daytime solar radiation insolation categories (Turner, 1964; EPA, 1995)."""
    STRONG = "STRONG"       # > 600 W/m² or solar elevation > 60°
    MODERATE = "MODERATE"   # 300 - 600 W/m² or solar elevation 35° - 60°
    SLIGHT = "SLIGHT"       # < 300 W/m² (daytime) or solar elevation 15° - 35°


def determine_insolation_category(
    solar_radiation: Optional[float] = None,
    solar_elevation_deg: Optional[float] = None,
) -> InsolationCategory:
    """
    Determine daytime solar insolation category from solar flux (W/m²) or solar elevation angle.

    Parameters
    ----------
    solar_radiation : float, optional
        Incoming solar irradiance in Watts per square meter (W/m²). Must be >= 0.
    solar_elevation_deg : float, optional
        Solar elevation angle above the horizon in degrees (0° to 90°).

    Returns
    -------
    InsolationCategory
        STRONG, MODERATE, or SLIGHT.

    Raises
    ------
    ValueError
        If neither or both invalid inputs are provided, or values are out of bounds.
    """
    if solar_radiation is not None:
        if not math.isfinite(solar_radiation) or solar_radiation < 0.0:
            raise ValueError(
                f"solar_radiation must be a non-negative finite number (W/m²), got {solar_radiation}"
            )
        if solar_radiation > 600.0:
            return InsolationCategory.STRONG
        elif solar_radiation >= 300.0:
            return InsolationCategory.MODERATE
        else:
            return InsolationCategory.SLIGHT

    if solar_elevation_deg is not None:
        if not math.isfinite(solar_elevation_deg) or not (0.0 <= solar_elevation_deg <= 90.0):
            raise ValueError(
                f"solar_elevation_deg must be between 0 and 90 degrees, got {solar_elevation_deg}"
            )
        if solar_elevation_deg > 60.0:
            return InsolationCategory.STRONG
        elif solar_elevation_deg >= 35.0:
            return InsolationCategory.MODERATE
        else:
            return InsolationCategory.SLIGHT

    raise ValueError(
        "Either 'solar_radiation' (W/m²) or 'solar_elevation_deg' (degrees) must be provided."
    )


def classify_stability(
    wind_speed: float,
    solar_radiation: Optional[float] = None,
    solar_elevation_deg: Optional[float] = None,
    cloud_cover: Optional[float] = None,
    is_daytime: Optional[bool] = None,
) -> StabilityClass:
    """
    Classify atmospheric stability into Pasquill-Gifford classes A-F using standard EPA/PGT rules.

    Parameters
    ----------
    wind_speed : float
        Surface horizontal wind speed at 10 meters height in meters per second (m/s).
        Must be strictly positive (u > 0). Calm conditions (u <= 0) violate steady-state
        Gaussian advection assumptions.
    solar_radiation : float, optional
        Downwelling solar irradiance in W/m² (daytime).
    solar_elevation_deg : float, optional
        Solar elevation angle in degrees (0 to 90) (daytime alternative).
    cloud_cover : float, optional
        Fractional cloud cover in range [0.0, 1.0] (or octa integer 0-8).
    is_daytime : bool, optional
        Explicit flag indicating daytime (True) or nighttime (False). If omitted,
        inferred from solar_radiation (> 0) or solar_elevation_deg (> 0).

    Returns
    -------
    StabilityClass
        Pasquill-Gifford stability class (A, B, C, D, E, or F).

    Raises
    ------
    ValueError
        If inputs are missing, out of range, or physically inconsistent.
    """
    # 1. Validate wind speed
    if not math.isfinite(wind_speed) or wind_speed <= 0.0:
        raise ValueError(
            f"Wind speed must be a strictly positive finite number (u > 0 m/s), got {wind_speed}. "
            "Calm conditions (u <= 0) cannot be simulated using standard Gaussian advection models."
        )

    # 2. Normalize and validate cloud cover if provided
    norm_cloud_cover: Optional[float] = None
    if cloud_cover is not None:
        if not math.isfinite(cloud_cover) or cloud_cover < 0.0:
            raise ValueError(f"Cloud cover must be non-negative, got {cloud_cover}")
        if cloud_cover > 8.0:
            # If specified as percentage (e.g. 0-100)
            if cloud_cover <= 100.0:
                norm_cloud_cover = cloud_cover / 100.0
            else:
                raise ValueError(
                    f"Cloud cover out of valid range (expected fraction [0, 1], octas [0, 8], or % [0, 100]), got {cloud_cover}"
                )
        elif cloud_cover > 1.0:
            # Interpreted as octas (0-8)
            norm_cloud_cover = cloud_cover / 8.0
        else:
            norm_cloud_cover = cloud_cover

    # 3. Determine day vs night
    if is_daytime is None:
        if solar_radiation is not None and solar_radiation > 0.0:
            is_daytime = True
        elif solar_elevation_deg is not None and solar_elevation_deg > 0.0:
            is_daytime = True
        elif solar_radiation == 0.0 or solar_elevation_deg == 0.0:
            is_daytime = False
        else:
            raise ValueError(
                "Unable to determine daytime vs nighttime. Provide 'is_daytime', 'solar_radiation', or 'solar_elevation_deg'."
            )

    # 4. Overcast conditions check (heavy cloud cover >= 7/8 or >= 87.5% is always Class D, neutral)
    if norm_cloud_cover is not None and norm_cloud_cover >= 0.875:
        return StabilityClass.D

    # 5. Daytime classification table
    if is_daytime:
        insolation = determine_insolation_category(
            solar_radiation=solar_radiation,
            solar_elevation_deg=solar_elevation_deg,
        )

        if insolation == InsolationCategory.STRONG:
            if wind_speed < 2.0:
                return StabilityClass.A
            elif wind_speed < 3.0:
                return StabilityClass.A  # A-B mapped to A
            elif wind_speed < 5.0:
                return StabilityClass.B
            else:  # wind_speed >= 5.0
                return StabilityClass.C

        elif insolation == InsolationCategory.MODERATE:
            if wind_speed < 2.0:
                return StabilityClass.B  # A-B mapped to B
            elif wind_speed < 3.0:
                return StabilityClass.B
            elif wind_speed < 5.0:
                return StabilityClass.C  # B-C mapped to C
            elif wind_speed < 6.0:
                return StabilityClass.C
            else:  # wind_speed >= 6.0
                return StabilityClass.D

        else:  # InsolationCategory.SLIGHT
            if wind_speed < 2.0:
                return StabilityClass.B
            elif wind_speed < 3.0:
                return StabilityClass.C
            elif wind_speed < 5.0:
                return StabilityClass.C
            else:  # wind_speed >= 5.0
                return StabilityClass.D

    # 6. Nighttime classification table
    else:
        # If cloud cover is not specified for nighttime, require it
        if norm_cloud_cover is None:
            raise ValueError(
                "Nighttime stability classification requires 'cloud_cover' (fraction [0, 1] or octas [0, 8])."
            )

        # Nighttime category:
        # Moderately cloudy (>= 4/8 or >= 50% cloud cover):
        if norm_cloud_cover >= 0.5:
            if wind_speed < 2.0:
                return StabilityClass.E
            elif wind_speed < 3.0:
                return StabilityClass.E
            elif wind_speed < 5.0:
                return StabilityClass.D
            else:  # wind_speed >= 5.0
                return StabilityClass.D
        # Clear to partly cloudy (< 4/8 or < 50% cloud cover):
        else:
            if wind_speed < 2.0:
                return StabilityClass.F
            elif wind_speed < 3.0:
                return StabilityClass.F
            elif wind_speed < 5.0:
                return StabilityClass.E
            else:  # wind_speed >= 5.0
                return StabilityClass.D
