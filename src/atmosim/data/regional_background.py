"""
Regional Background PM2.5 Ingestion & Inflow Connector Module for AtmosSim.

Connects to the Copernicus Atmosphere Monitoring Service (CAMS) Global Atmospheric
Composition Reanalysis / Forecast via Open-Meteo Air Quality API to provide regional
synoptic background particulate concentrations.

In high-inversion / transboundary pollution basins like Delhi / Indo-Gangetic Plain (IGP),
regional background (crop residue burning, transboundary dust, regional secondary aerosols)
typically accounts for 70–90% of total ambient PM2.5 during severe winter episodes. Coupling
local dispersion models with this inflow connector prevents negative correlation artifacts
and enables realistic ground-truth calibration.

References
----------
1. Inness et al. (2019). The CAMS reanalysis of atmospheric composition. Atmos. Chem. Phys.
2. Open-Meteo Air Quality API (https://open-meteo.com/en/docs/air-quality-api)
3. IIT Kanpur / TERI (2018). Comprehensive Study on Air Pollution and Green House Gases in Delhi.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import math
import requests

from atmosim.data.cache import DataCache


class RegionalBackgroundSource(str, Enum):
    """Source provider for regional background PM2.5."""
    CAMS_GLOBAL = "CAMS_GLOBAL"
    SEASONAL_BASELINE = "SEASONAL_BASELINE"
    SYNTHETIC = "SYNTHETIC"


@dataclass
class HourlyRegionalRecord:
    """Single normalized hourly regional background observation."""
    timestamp: datetime  # UTC
    pm2_5_ug_m3: float   # µg/m³
    pm10_ug_m3: Optional[float] = None  # µg/m³
    source: str = "CAMS_GLOBAL"


# Empirical seasonal baseline background for the Indo-Gangetic Plain / Delhi
# (derived from IIT Kanpur / TERI 2018 non-local background measurements)
IGP_SEASONAL_BACKGROUND_PM25: Dict[int, float] = {
    1: 140.0,   # January (Peak winter inversion)
    2: 95.0,    # February
    3: 65.0,    # March
    4: 60.0,    # April
    5: 55.0,    # May (Pre-monsoon dust)
    6: 40.0,    # June
    7: 30.0,    # July (Monsoon washout)
    8: 25.0,    # August (Monsoon washout)
    9: 35.0,    # September
    10: 90.0,   # October (Stubble burning onset)
    11: 175.0,  # November (Peak episodic stubble + calm inversion)
    12: 155.0,  # December (Severe winter inversion)
}


@dataclass
class RegionalBackgroundTimeSeries:
    """
    Normalized continuous regional background time-series covering simulation window.
    """
    latitude: float
    longitude: float
    start_time: datetime  # UTC
    end_time: datetime    # UTC
    records: List[HourlyRegionalRecord]
    provenance: Dict[str, Any]
    quality_flags: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.records:
            raise ValueError("RegionalBackgroundTimeSeries cannot be empty.")
        if self.start_time >= self.end_time:
            raise ValueError(f"start_time ({self.start_time}) must be strictly before end_time ({self.end_time})")

    @property
    def timestamps_utc(self) -> List[datetime]:
        return [r.timestamp for r in self.records]

    @property
    def time_offsets_seconds(self) -> List[float]:
        t0 = self.start_time.timestamp()
        return [r.timestamp.timestamp() - t0 for r in self.records]

    def get_mean_pm25(self) -> float:
        """Calculate mean background PM2.5 across the entire window."""
        return float(sum(r.pm2_5_ug_m3 for r in self.records) / len(self.records))

    def get_interpolated_pm25(self, t_seconds: float) -> float:
        """
        Interpolate regional background PM2.5 (µg/m³) at t_seconds from start_time.

        Parameters
        ----------
        t_seconds : float
            Seconds elapsed from start_time.

        Returns
        -------
        float
            Background PM2.5 concentration in µg/m³.
        """
        offsets = self.time_offsets_seconds
        t_clamped = max(offsets[0], min(t_seconds, offsets[-1]))

        if t_clamped <= offsets[0]:
            return self.records[0].pm2_5_ug_m3
        if t_clamped >= offsets[-1]:
            return self.records[-1].pm2_5_ug_m3

        # Linear binary search
        low = 0
        high = len(offsets) - 1
        while high - low > 1:
            mid = (low + high) // 2
            if offsets[mid] <= t_clamped:
                low = mid
            else:
                high = mid

        dt = offsets[high] - offsets[low]
        if dt <= 0.0:
            return self.records[low].pm2_5_ug_m3

        weight_high = (t_clamped - offsets[low]) / dt
        c_low = self.records[low].pm2_5_ug_m3
        c_high = self.records[high].pm2_5_ug_m3
        return float(c_low + weight_high * (c_high - c_low))


class RegionalBackgroundConnector:
    """
    Ingestion connector for regional synoptic PM2.5 background via CAMS Air Quality API
    with automatic offline caching and documented seasonal fallback.

    Parameters
    ----------
    cache : Optional[DataCache], optional
        Deterministic caching instance.
    timeout_seconds : int, default=15
        HTTP request timeout in seconds.
    force_fallback : bool, default=False
        If True, forces use of empirical seasonal baseline without network request.
    """

    AIR_QUALITY_ENDPOINT = "https://air-quality-api.open-meteo.com/v1/air-quality"

    def __init__(
        self,
        cache: Optional[DataCache] = None,
        timeout_seconds: int = 15,
        force_fallback: bool = False,
    ) -> None:
        self.cache = cache or DataCache()
        self.timeout_seconds = timeout_seconds
        self.force_fallback = force_fallback

    def query(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
    ) -> RegionalBackgroundTimeSeries:
        """
        Query regional background PM2.5 across the temporal simulation window.

        Parameters
        ----------
        latitude : float
            Target latitude (-90 to 90).
        longitude : float
            Target longitude (-180 to 180).
        start_time : datetime
            Window start time (UTC).
        end_time : datetime
            Window end time (UTC).

        Returns
        -------
        RegionalBackgroundTimeSeries
            Normalized continuous hourly background time series.
        """
        start_utc = start_time if start_time.tzinfo else start_time.replace(tzinfo=timezone.utc)
        end_utc = end_time if end_time.tzinfo else end_time.replace(tzinfo=timezone.utc)

        if start_utc >= end_utc:
            raise ValueError(f"start_time ({start_utc}) must be strictly before end_time ({end_utc})")

        if self.force_fallback:
            return self._build_seasonal_fallback(latitude, longitude, start_utc, end_utc, reason="force_fallback=True")

        start_date_str = start_utc.strftime("%Y-%m-%d")
        end_date_str = end_utc.strftime("%Y-%m-%d")

        params = {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "start_date": start_date_str,
            "end_date": end_date_str,
            "hourly": "pm2_5,pm10",
            "timezone": "UTC",
        }

        cache_key = self.cache.generate_key("cams_air_quality", params)
        raw_json = self.cache.get(cache_key)

        if raw_json is None:
            try:
                resp = requests.get(
                    self.AIR_QUALITY_ENDPOINT,
                    params=params,
                    timeout=self.timeout_seconds,
                )
                resp.raise_for_status()
                raw_json = resp.json()
                self.cache.set(cache_key, raw_json)
            except Exception as exc:
                # Fall back gracefully to documented seasonal baseline
                return self._build_seasonal_fallback(
                    latitude,
                    longitude,
                    start_utc,
                    end_utc,
                    reason=f"Network/API error: {exc}",
                )

        try:
            return self._parse_response(
                raw_json=raw_json,
                latitude=latitude,
                longitude=longitude,
                start_time=start_utc,
                end_time=end_utc,
                params=params,
            )
        except Exception as exc:
            return self._build_seasonal_fallback(
                latitude,
                longitude,
                start_utc,
                end_utc,
                reason=f"Parse error: {exc}",
            )

    def _parse_response(
        self,
        raw_json: Dict[str, Any],
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
        params: Dict[str, Any],
    ) -> RegionalBackgroundTimeSeries:
        """Parse raw Open-Meteo Air Quality JSON response."""
        if "hourly" not in raw_json or "time" not in raw_json["hourly"]:
            raise ValueError(f"Invalid Air Quality response: missing hourly.time in {raw_json}")

        hourly = raw_json["hourly"]
        time_strs = hourly["time"]
        pm25_vals = hourly.get("pm2_5", [None] * len(time_strs))
        pm10_vals = hourly.get("pm10", [None] * len(time_strs))

        records: List[HourlyRegionalRecord] = []
        imputed_count = 0

        for i, t_iso in enumerate(time_strs):
            dt = datetime.fromisoformat(t_iso)
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)

            v25 = pm25_vals[i]
            v10 = pm10_vals[i] if i < len(pm10_vals) else None

            if v25 is None or not math.isfinite(v25):
                imputed_count += 1
                v25 = IGP_SEASONAL_BACKGROUND_PM25.get(dt.month, 75.0)

            records.append(
                HourlyRegionalRecord(
                    timestamp=dt,
                    pm2_5_ug_m3=float(v25),
                    pm10_ug_m3=float(v10) if v10 is not None and math.isfinite(v10) else None,
                    source="CAMS_GLOBAL",
                )
            )

        provenance = {
            "provider": "Open-Meteo CAMS Air Quality API",
            "endpoint": self.AIR_QUALITY_ENDPOINT,
            "query_parameters": params,
            "source_type": RegionalBackgroundSource.CAMS_GLOBAL.value,
            "imputed_records_count": imputed_count,
            "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return RegionalBackgroundTimeSeries(
            latitude=latitude,
            longitude=longitude,
            start_time=start_time,
            end_time=end_time,
            records=records,
            provenance=provenance,
            quality_flags={"imputed_records": imputed_count, "is_fallback": False},
        )

    def _build_seasonal_fallback(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
        reason: str,
    ) -> RegionalBackgroundTimeSeries:
        """Construct deterministic seasonal baseline background when API is unavailable."""
        from datetime import timedelta
        current = start_time
        records: List[HourlyRegionalRecord] = []

        while current <= end_time:
            base_pm25 = IGP_SEASONAL_BACKGROUND_PM25.get(current.month, 75.0)
            # Add subtle diurnal variation (higher at night/early morning during inversion)
            hour = current.hour
            diurnal_mult = 1.15 if (hour <= 6 or hour >= 21) else (0.85 if 11 <= hour <= 16 else 1.0)
            records.append(
                HourlyRegionalRecord(
                    timestamp=current,
                    pm2_5_ug_m3=float(base_pm25 * diurnal_mult),
                    pm10_ug_m3=float(base_pm25 * diurnal_mult * 1.8),
                    source="SEASONAL_BASELINE",
                )
            )
            current += timedelta(hours=1)

        provenance = {
            "provider": "Empirical Seasonal Baseline (IIT Kanpur / TERI 2018)",
            "fallback_reason": reason,
            "source_type": RegionalBackgroundSource.SEASONAL_BASELINE.value,
            "is_fallback": True,
        }

        return RegionalBackgroundTimeSeries(
            latitude=latitude,
            longitude=longitude,
            start_time=start_time,
            end_time=end_time,
            records=records,
            provenance=provenance,
            quality_flags={"is_fallback": True, "fallback_reason": reason},
        )
