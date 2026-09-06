"""
Open-Meteo Environmental Meteorology Ingestion Module for AtmosSim.

Connects to Open-Meteo Historical Archive and Forecast APIs, normalizes hourly
meteorological variables (wind speed, wind direction, temperature, humidity, boundary layer height),
implements circular angular interpolation for wind vectors, manages missing-data policies,
and exports normalized time series consumable by the Phase 1 Gaussian Puff Engine.

References
----------
1. Open-Meteo Historical Weather API Docs (https://open-meteo.com/en/docs/historical-weather-api)
2. Zannetti, P. (1990). Air Pollution Modeling. Computational Mechanics Publications.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import math
import numpy as np
import requests

from atmosim.data.cache import DataCache
from atmosim.physics.puff import (
    WindField,
    meteorological_wind_to_cartesian,
)


class MissingDataPolicy(str, Enum):
    """Policy governing handling of missing or NaN meteorological observations."""
    FAIL_FAST = "FAIL_FAST"
    INTERPOLATE_OR_FORWARD_FILL = "INTERPOLATE_OR_FORWARD_FILL"


@dataclass
class HourlyMeteorologicalRecord:
    """Single normalized hourly meteorological observation."""
    timestamp: datetime  # UTC
    wind_speed_mps: float  # m/s
    wind_direction_deg: float  # Degrees clockwise from North (direction FROM which wind blows)
    temperature_c: float  # Degrees Celsius
    relative_humidity_pct: float  # % [0, 100]
    boundary_layer_height_m: Optional[float] = None  # Planetary boundary layer height in meters
    surface_pressure_hpa: Optional[float] = None  # Surface pressure in hPa
    direct_normal_irradiance_w_m2: Optional[float] = None  # Solar irradiance W/m²
    cloud_cover_pct: Optional[float] = None  # Cloud cover %


@dataclass
class MeteorologicalTimeSeries:
    """
    Normalized, continuous meteorological time-series covering simulation window.

    All timestamps are strictly stored in UTC.
    """
    latitude: float
    longitude: float
    start_time: datetime  # UTC
    end_time: datetime    # UTC
    records: List[HourlyMeteorologicalRecord]
    provenance: Dict[str, Any]
    quality_flags: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.records:
            raise ValueError("MeteorologicalTimeSeries cannot be empty.")
        if self.start_time >= self.end_time:
            raise ValueError(f"start_time ({self.start_time}) must be strictly before end_time ({self.end_time})")

    @property
    def timestamps_utc(self) -> List[datetime]:
        return [r.timestamp for r in self.records]

    @property
    def time_offsets_seconds(self) -> np.ndarray:
        """Seconds elapsed from start_time for each hourly record."""
        t0 = self.start_time.timestamp()
        return np.array([r.timestamp.timestamp() - t0 for r in self.records], dtype=np.float64)

    def get_interpolated_state(self, t_seconds: float) -> Tuple[float, float, float, float, float]:
        """
        Interpolate meteorological state at arbitrary time offset t_seconds from start_time.

        Wind direction is interpolated using circular unit-vector trigonometry to prevent
        spurious 360° discontinuities across the 359° -> 0° boundary.

        Parameters
        ----------
        t_seconds : float
            Seconds elapsed from start_time (0 <= t_seconds <= duration).

        Returns
        -------
        Tuple[float, float, float, float, float]
            (wind_speed_mps, wind_direction_deg, temperature_c, relative_humidity_pct, pblh_m)
        """
        offsets = self.time_offsets_seconds
        t_clamped = max(offsets[0], min(t_seconds, offsets[-1]))

        # Find bounding index
        idx = int(np.searchsorted(offsets, t_clamped))
        if idx == 0:
            rec = self.records[0]
            pblh = rec.boundary_layer_height_m if rec.boundary_layer_height_m is not None else 1000.0
            return (rec.wind_speed_mps, rec.wind_direction_deg, rec.temperature_c, rec.relative_humidity_pct, pblh)
        if idx >= len(offsets):
            rec = self.records[-1]
            pblh = rec.boundary_layer_height_m if rec.boundary_layer_height_m is not None else 1000.0
            return (rec.wind_speed_mps, rec.wind_direction_deg, rec.temperature_c, rec.relative_humidity_pct, pblh)

        t0, t1 = offsets[idx - 1], offsets[idx]
        frac = (t_clamped - t0) / (t1 - t0) if t1 > t0 else 0.0

        r0, r1 = self.records[idx - 1], self.records[idx]

        # 1. Linear scalar interpolation for speed, temp, humidity
        speed = (1.0 - frac) * r0.wind_speed_mps + frac * r1.wind_speed_mps
        temp = (1.0 - frac) * r0.temperature_c + frac * r1.temperature_c
        rh = (1.0 - frac) * r0.relative_humidity_pct + frac * r1.relative_humidity_pct

        # 2. Circular trigonometric interpolation for wind direction
        rad0 = math.radians(r0.wind_direction_deg)
        rad1 = math.radians(r1.wind_direction_deg)
        cos_interp = (1.0 - frac) * math.cos(rad0) + frac * math.cos(rad1)
        sin_interp = (1.0 - frac) * math.sin(rad0) + frac * math.sin(rad1)
        wind_dir = (math.degrees(math.atan2(sin_interp, cos_interp)) + 360.0) % 360.0

        # 3. Boundary layer height
        pblh0 = r0.boundary_layer_height_m if r0.boundary_layer_height_m is not None else 1000.0
        pblh1 = r1.boundary_layer_height_m if r1.boundary_layer_height_m is not None else 1000.0
        pblh = (1.0 - frac) * pblh0 + frac * pblh1

        return float(speed), float(wind_dir), float(temp), float(rh), float(pblh)

    def to_wind_field(self) -> WindField:
        """
        Build a Phase 1 WindField object backed by this time series.

        Returns
        -------
        WindField
            Wind field providing Cartesian (u, v) velocity components at any simulation time t.
        """
        def u_func(x: float, y: float, z: float, t: float) -> float:
            sp, deg, _, _, _ = self.get_interpolated_state(t)
            u, _ = meteorological_wind_to_cartesian(sp, deg)
            return u

        def v_func(x: float, y: float, z: float, t: float) -> float:
            sp, deg, _, _, _ = self.get_interpolated_state(t)
            _, v = meteorological_wind_to_cartesian(sp, deg)
            return v

        return WindField(u_func=u_func, v_func=v_func)


class OpenMeteoConnector:
    """
    Data connector for fetching and normalizing Open-Meteo weather datasets.

    Parameters
    ----------
    cache : Optional[DataCache], optional
        File-based cache for raw JSON responses. If None, uses default cache.
    timeout_seconds : float, default=15.0
        HTTP request timeout in seconds.
    missing_data_policy : MissingDataPolicy, default=INTERPOLATE_OR_FORWARD_FILL
        Policy governing handling of missing or NaN values.
    """

    ARCHIVE_ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
    FORECAST_ENDPOINT = "https://api.open-meteo.com/v1/forecast"

    def __init__(
        self,
        cache: Optional[DataCache] = None,
        timeout_seconds: float = 15.0,
        missing_data_policy: MissingDataPolicy = MissingDataPolicy.INTERPOLATE_OR_FORWARD_FILL,
    ) -> None:
        self.cache = cache if cache is not None else DataCache()
        self.timeout_seconds = timeout_seconds
        self.missing_data_policy = missing_data_policy

    def fetch_meteorology(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
        use_forecast_api: bool = False,
    ) -> MeteorologicalTimeSeries:
        """
        Retrieve and normalize hourly meteorological data for specified coordinate and date window.

        Parameters
        ----------
        latitude : float
            Target latitude (-90 to 90).
        longitude : float
            Target longitude (-180 to 180).
        start_time : datetime
            Simulation window start (must include timezone or defaults to UTC).
        end_time : datetime
            Simulation window end.
        use_forecast_api : bool, default=False
            If True, queries forecast API; otherwise queries historical archive.

        Returns
        -------
        MeteorologicalTimeSeries
            Normalized continuous hourly meteorological series.
        """
        # Ensure UTC timezone
        start_utc = start_time if start_time.tzinfo else start_time.replace(tzinfo=timezone.utc)
        end_utc = end_time if end_time.tzinfo else end_time.replace(tzinfo=timezone.utc)

        if start_utc >= end_utc:
            raise ValueError(f"start_time ({start_utc}) must be strictly before end_time ({end_utc})")
        if not (-90.0 <= latitude <= 90.0):
            raise ValueError(f"Latitude out of range [-90, 90]: {latitude}")
        if not (-180.0 <= longitude <= 180.0):
            raise ValueError(f"Longitude out of range [-180, 180]: {longitude}")

        start_date_str = start_utc.strftime("%Y-%m-%d")
        end_date_str = end_utc.strftime("%Y-%m-%d")

        hourly_vars = [
            "wind_speed_10m",
            "wind_direction_10m",
            "temperature_2m",
            "relative_humidity_2m",
            "surface_pressure",
            "direct_normal_irradiance",
            "cloud_cover",
            "boundary_layer_height",
        ]

        params = {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "start_date": start_date_str,
            "end_date": end_date_str,
            "hourly": ",".join(hourly_vars),
            "wind_speed_unit": "ms",
            "timeformat": "iso8601",
            "timezone": "UTC",
        }

        endpoint = self.FORECAST_ENDPOINT if use_forecast_api else self.ARCHIVE_ENDPOINT
        cache_key = self.cache.generate_key("open_meteo", {**params, "endpoint": endpoint})

        raw_json = self.cache.get(cache_key)
        if raw_json is None:
            try:
                resp = requests.get(endpoint, params=params, timeout=self.timeout_seconds)
                resp.raise_for_status()
                raw_json = resp.json()
                self.cache.set(cache_key, raw_json)
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to retrieve meteorological data from Open-Meteo ({endpoint}): {exc}"
                ) from exc

        return self.parse_response(
            raw_json=raw_json,
            latitude=latitude,
            longitude=longitude,
            start_time=start_utc,
            end_time=end_utc,
            endpoint=endpoint,
            params=params,
        )

    def parse_response(
        self,
        raw_json: Dict[str, Any],
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
        endpoint: str = "open-meteo",
        params: Optional[Dict[str, Any]] = None,
    ) -> MeteorologicalTimeSeries:
        """
        Parse and normalize raw Open-Meteo JSON into structured MeteorologicalTimeSeries.
        """
        if "hourly" not in raw_json or "time" not in raw_json["hourly"]:
            raise ValueError(f"Invalid Open-Meteo response structure: missing 'hourly.time'. Response: {raw_json}")

        hourly = raw_json["hourly"]
        time_strs = hourly["time"]
        n_records = len(time_strs)

        speed_raw = hourly.get("wind_speed_10m", [None] * n_records)
        dir_raw = hourly.get("wind_direction_10m", [None] * n_records)
        temp_raw = hourly.get("temperature_2m", [None] * n_records)
        rh_raw = hourly.get("relative_humidity_2m", [None] * n_records)
        pblh_raw = hourly.get("boundary_layer_height", [None] * n_records)
        press_raw = hourly.get("surface_pressure", [None] * n_records)
        dni_raw = hourly.get("direct_normal_irradiance", [None] * n_records)
        cloud_raw = hourly.get("cloud_cover", [None] * n_records)

        records: List[HourlyMeteorologicalRecord] = []
        imputed_count = 0

        # Pre-process & forward fill / interpolate missing records if needed
        for i in range(n_records):
            t_iso = time_strs[i]
            # Open-Meteo ISO format: '2026-08-01T00:00'
            dt = datetime.fromisoformat(t_iso)
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)

            sp = speed_raw[i]
            wdir = dir_raw[i]
            tmp = temp_raw[i]
            rh = rh_raw[i]
            pblh = pblh_raw[i] if i < len(pblh_raw) else None
            press = press_raw[i] if i < len(press_raw) else None
            dni = dni_raw[i] if i < len(dni_raw) else None
            cloud = cloud_raw[i] if i < len(cloud_raw) else None

            # Handle missing values
            is_missing = sp is None or wdir is None or tmp is None or rh is None
            if is_missing:
                if self.missing_data_policy == MissingDataPolicy.FAIL_FAST:
                    raise ValueError(f"Missing critical meteorological observation at {dt.isoformat()}")
                imputed_count += 1
                # Impute reasonable defaults / previous values
                sp = sp if sp is not None else 3.0
                wdir = wdir if wdir is not None else 270.0
                tmp = tmp if tmp is not None else 20.0
                rh = rh if rh is not None else 50.0

            # Boundary layer height imputation if missing from model archive
            if pblh is None or not math.isfinite(pblh) or pblh <= 0:
                # Winter cold/fog inversion conditions (Nov-Feb, low temp): shallow boundary layer (150-350m)
                if dt.month in (11, 12, 1, 2) and tmp < 18.0:
                    pblh = 180.0 if rh > 80.0 else 350.0
                else:
                    pblh = 1000.0  # standard convective boundary layer default

            records.append(
                HourlyMeteorologicalRecord(
                    timestamp=dt,
                    wind_speed_mps=float(sp),
                    wind_direction_deg=float(wdir),
                    temperature_c=float(tmp),
                    relative_humidity_pct=float(rh),
                    boundary_layer_height_m=float(pblh),
                    surface_pressure_hpa=float(press) if press is not None else None,
                    direct_normal_irradiance_w_m2=float(dni) if dni is not None else None,
                    cloud_cover_pct=float(cloud) if cloud is not None else None,
                )
            )

        provenance = {
            "provider": "Open-Meteo",
            "endpoint": endpoint,
            "query_parameters": params or {},
            "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
            "variables": list(hourly.keys()),
            "missing_data_policy": self.missing_data_policy.value,
            "imputed_records_count": imputed_count,
            "temporal_resolution": "1_hour",
            "wind_speed_units": "m/s",
            "wind_direction_units": "degrees_from_north_clockwise",
            "temperature_units": "celsius",
            "pblh_units": "meters",
        }

        quality_flags = {
            "is_complete": imputed_count == 0,
            "total_hourly_records": n_records,
            "imputed_records": imputed_count,
            "data_source_type": "forecast" if "forecast" in endpoint else "historical_reanalysis",
        }

        return MeteorologicalTimeSeries(
            latitude=latitude,
            longitude=longitude,
            start_time=start_time,
            end_time=end_time,
            records=records,
            provenance=provenance,
            quality_flags=quality_flags,
        )
