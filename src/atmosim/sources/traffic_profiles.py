"""
Temporal Traffic Activity Profiles Module for AtmosSim.

Implements normalized diurnal (hour-of-day) and weekly (weekday vs. weekend)
activity profiles for scaling base proxy traffic emissions.

Normalization Convention
------------------------
The 24-hour diurnal profile f_h satisfies:
(1 / 24) * sum_{h=0}^{23} f_h = 1.0
This ensures that the daily mean activity equals 1.0, preserving daily total emissions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
import numpy as np


@dataclass
class TemporalTrafficProfile:
    """
    Normalized temporal activity profile.

    Parameters
    ----------
    profile_name : str
        Human-readable name for the profile.
    hourly_factors : List[float]
        24 normalized hourly multipliers for hours 0 through 23.
    weekend_multiplier : float, default=0.85
        Scaling factor applied on Saturday and Sunday (e.g. 0.85 for 15% reduction).
    monthly_multipliers : Optional[Dict[int, float]], optional
        Optional 1-12 monthly scaling factors (e.g. monsoon moisture suppression).
    source_reference : str
        Literature citation or synthetic specification note.
    """
    profile_name: str
    hourly_factors: List[float]
    weekend_multiplier: float = 0.85
    monthly_multipliers: Optional[Dict[int, float]] = None
    source_reference: str = "Synthetic/Default Urban Diurnal Profile"

    def __post_init__(self):
        if len(self.hourly_factors) != 24:
            raise ValueError(f"hourly_factors must contain exactly 24 values, got {len(self.hourly_factors)}")
        if any(f < 0 for f in self.hourly_factors):
            raise ValueError("Hourly factors must be non-negative.")

        # Enforce exact mean normalization: (1/24) * sum(f_h) = 1.0
        mean_factor = float(np.mean(self.hourly_factors))
        if mean_factor <= 0:
            raise ValueError("Mean hourly factor must be strictly positive.")

        # Re-normalize if slight rounding discrepancies exist
        self.hourly_factors = [float(f / mean_factor) for f in self.hourly_factors]

    def get_multiplier(self, dt: datetime) -> float:
        """
        Evaluate normalized activity multiplier for given datetime.

        Parameters
        ----------
        dt : datetime
            Observation or simulation timestamp.

        Returns
        -------
        float
            Dimensionless activity multiplier.
        """
        hour = dt.hour
        base_h = self.hourly_factors[hour]
        is_weekend = dt.weekday() >= 5  # 5=Saturday, 6=Sunday
        weekend_factor = self.weekend_multiplier if is_weekend else 1.0
        month_factor = self.monthly_multipliers.get(dt.month, 1.0) if self.monthly_multipliers else 1.0
        return float(base_h * weekend_factor * month_factor)

    @classmethod
    def default_urban_diurnal(cls) -> "TemporalTrafficProfile":
        """
        Create standard bimodal urban diurnal traffic profile:
        - Morning peak: ~08:00 - 09:00 (factor ~1.7)
        - Evening peak: ~17:00 - 19:00 (factor ~1.8)
        - Overnight trough: ~02:00 - 04:00 (factor ~0.2)
        """
        # Unnormalized 24-hour shape
        raw_shape = [
            0.25, 0.18, 0.15, 0.15, 0.22, 0.50,  # 00:00 - 05:00
            0.95, 1.60, 1.85, 1.55, 1.25, 1.15,  # 06:00 - 11:00
            1.10, 1.15, 1.20, 1.40, 1.70, 1.95,  # 12:00 - 17:00
            1.80, 1.45, 1.05, 0.75, 0.50, 0.35,  # 18:00 - 23:00
        ]
        return cls(
            profile_name="Standard_Urban_Bimodal_Diurnal",
            hourly_factors=raw_shape,
            weekend_multiplier=0.85,
            source_reference="AtmosSim Default Urban Bimodal Traffic Activity Parameterization",
        )

    @classmethod
    def default_indian_urban(cls) -> "TemporalTrafficProfile":
        """
        Indian urban profile with seasonal road-dust / moisture scaling (IIT Kanpur / CPCB):
        - Peak dry winter emissions (Nov-Feb: 1.0)
        - Summer pre-monsoon (Mar-May: 0.85)
        - Monsoon washout / moisture suppression (Jun-Sep: 0.25 - 0.40)
        - Post-monsoon transition (Oct: 0.75)
        """
        raw_shape = [
            0.25, 0.18, 0.15, 0.15, 0.22, 0.50,  # 00:00 - 05:00
            0.95, 1.60, 1.85, 1.55, 1.25, 1.15,  # 06:00 - 11:00
            1.10, 1.15, 1.20, 1.40, 1.70, 1.95,  # 12:00 - 17:00
            1.80, 1.45, 1.05, 0.75, 0.50, 0.35,  # 18:00 - 23:00
        ]
        monthly_moisture = {
            1: 1.0, 2: 0.90, 3: 0.85, 4: 0.85, 5: 0.85,
            6: 0.40, 7: 0.25, 8: 0.25, 9: 0.35, 10: 0.75, 11: 1.0, 12: 1.0
        }
        return cls(
            profile_name="Indian_Urban_Seasonal_Diurnal",
            hourly_factors=raw_shape,
            weekend_multiplier=0.85,
            monthly_multipliers=monthly_moisture,
            source_reference="IIT Kanpur (2018) & CPCB Indian Urban Fleet & Road Dust Seasonal Activity Profile",
        )

    @classmethod
    def uniform_constant(cls) -> "TemporalTrafficProfile":
        """Constant 1.0 profile across all 24 hours."""
        return cls(
            profile_name="Uniform_Constant",
            hourly_factors=[1.0] * 24,
            weekend_multiplier=1.0,
            source_reference="Uniform Flat Traffic Activity Profile",
        )
