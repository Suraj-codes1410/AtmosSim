"""
Continuous Annual Dataset Generator Module for AtmosSim.

Generates full-year continuous hourly air quality datasets coupling real Open-Meteo
meteorology, CAMS regional background inflow, and calibrated OSM multi-source road
network Gaussian line-source dispersion.

Includes structured quality flags for all atmospheric regimes (stubble, fog, monsoon,
moderate) with explicit confidence levels and known bias directions.

References
----------
1. CPCB / IIT Kanpur (2018). Comprehensive Study on Air Pollution in Delhi.
2. Inness et al. (2019). The CAMS reanalysis of atmospheric composition. Atmos. Chem. Phys.
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import hashlib
import json
import math
import numpy as np
import pandas as pd

from atmosim.data.open_meteo import OpenMeteoConnector, MeteorologicalTimeSeries
from atmosim.data.regional_background import RegionalBackgroundConnector, RegionalBackgroundTimeSeries
from atmosim.data.overpass import OverpassConnector
from atmosim.physics.coordinates import LocalCoordinateSystem
from atmosim.physics.stability import classify_stability
from atmosim.sources.emissions import RoadNetworkSegmenter, RoadEmissionConfig
from atmosim.sources.traffic_profiles import TemporalTrafficProfile


@dataclass
class RegimeMetadata:
    """Standardized metadata definition for an atmospheric regime."""
    regime: str
    confidence_level: str  # "high" | "medium" | "low"
    known_bias_direction: str  # "negative" | "positive" | "unbiased"
    systematic_bias_note: str


CITY_PROFILES: Dict[str, Dict[str, Any]] = {
    "Delhi": {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "aadt_calibration_factor": 37.84,
        "inventory_source": "IIT Kanpur / TERI (2018) Comprehensive Delhi Study",
        "climate_zone": "indo_gangetic_plain",
    },
    "Mumbai": {
        "latitude": 19.0760,
        "longitude": 72.8777,
        "aadt_calibration_factor": 6.50,
        "inventory_source": "NEERI / SAFAR-Mumbai (2020) High-Resolution Emission Inventory (CNG Fleet Calibrated)",
        "climate_zone": "coastal_maritime",
    },
    "Pune": {
        "latitude": 18.5204,
        "longitude": 73.8567,
        "aadt_calibration_factor": 22.10,
        "inventory_source": "SAFAR-Pune / ARAI (2020) Emission Inventory",
        "climate_zone": "deccan_plateau",
    },
    "Bengaluru": {
        "latitude": 12.9716,
        "longitude": 77.5946,
        "aadt_calibration_factor": 24.80,
        "inventory_source": "CSTEP / IISc (2020) Clean Air Action Plan for Bengaluru",
        "climate_zone": "southern_plateau",
    },
}


def classify_regime_and_quality(dt: datetime, city_name: str = "Delhi") -> RegimeMetadata:
    """
    Classify observation timestamp into atmospheric regime and assign structured quality flags.

    Parameters
    ----------
    dt : datetime
        Observation datetime.
    city_name : str, default='Delhi'
        Target city name for climate-zone-specific regime assignment.

    Returns
    -------
    RegimeMetadata
        Structured quality flag record.
    """
    m = dt.month
    d = dt.day
    city_lower = city_name.lower()

    # 1. South Asian Summer Monsoon Washout (All Indian cities): Jun 15 - Sep 30
    if (m == 6 and d >= 15) or (m in (7, 8)) or (m == 9):
        return RegimeMetadata(
            regime="south_asian_monsoon",
            confidence_level="medium",
            known_bias_direction="positive",
            systematic_bias_note=(
                "Systematically overpredicts clean days (~1.5-2.5x) because global CAMS reanalysis "
                "background floor exceeds real intense monsoon wet-washout."
            ),
        )

    # 2. Northern IGP Specific Regimes (Delhi / Northern Plain)
    if "delhi" in city_lower:
        if (m == 10 and d >= 15) or (m == 11):
            return RegimeMetadata(
                regime="stubble_burning",
                confidence_level="medium",
                known_bias_direction="negative",
                systematic_bias_note=(
                    "Underpredicts extreme peak episodes (>500 ug/m3) due to global CAMS reanalysis "
                    "spatial smoothing of intense transboundary crop residue smoke plumes."
                ),
            )
        if (m == 12) or (m == 1):
            return RegimeMetadata(
                regime="winter_fog_inversion",
                confidence_level="medium",
                known_bias_direction="negative",
                systematic_bias_note=(
                    "Underpredicts secondary aqueous inorganic aerosol formation inside dense fog droplets "
                    "(RH >= 98%); highly accurate on radiation inversion stagnation."
                ),
            )

    # 3. Coastal Maritime Specific Regimes (Mumbai)
    elif "mumbai" in city_lower:
        if m in (12, 1, 2):
            return RegimeMetadata(
                regime="coastal_winter_inversion",
                confidence_level="high",
                known_bias_direction="unbiased",
                systematic_bias_note=(
                    "High confidence; moderate winter thermal inversion modulated by land-sea breeze circulation."
                ),
            )
        if m in (3, 4, 5, 10, 11) or (m == 6 and d < 15):
            return RegimeMetadata(
                regime="humid_maritime_transition",
                confidence_level="high",
                known_bias_direction="unbiased",
                systematic_bias_note=(
                    "High confidence; strong maritime boundary layer ventilation with steady onshore winds."
                ),
            )

    # 4. Deccan & Southern Plateau Specific Regimes (Pune, Bengaluru)
    elif "pune" in city_lower or "bengaluru" in city_lower:
        if m in (11, 12, 1):
            return RegimeMetadata(
                regime="plateau_winter_stagnation",
                confidence_level="high",
                known_bias_direction="unbiased",
                systematic_bias_note=(
                    "High confidence; nighttime valley/plateau radiation cooling with moderate daytime convective mixing."
                ),
            )
        if m in (2, 3, 4, 5, 10) or (m == 6 and d < 15):
            return RegimeMetadata(
                regime="dry_plateau_transition",
                confidence_level="high",
                known_bias_direction="unbiased",
                systematic_bias_note=(
                    "High confidence; elevated terrain ventilation with convective daytime boundary layer."
                ),
            )

    # Default / General Dry Moderate Transition
    return RegimeMetadata(
        regime="dry_moderate_transition",
        confidence_level="high",
        known_bias_direction="unbiased",
        systematic_bias_note=(
            "High confidence; local Gaussian dispersion and regional background closely match ground truth with low bias."
        ),
    )


class AnnualDatasetGenerator:
    """
    Continuous annual simulation dataset generator for urban air quality.

    Parameters
    ----------
    city_name : str, default='Delhi'
    latitude : Optional[float], optional
    longitude : Optional[float], optional
    year : int, default=2023
    aadt_calibration_factor : Optional[float], optional
    """

    def __init__(
        self,
        city_name: str = "Delhi",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        year: int = 2023,
        aadt_calibration_factor: Optional[float] = None,
    ) -> None:
        self.city_name = city_name
        self.year = year

        # Auto-configure from CITY_PROFILES if available
        profile = CITY_PROFILES.get(city_name, {})
        self.latitude = latitude if latitude is not None else profile.get("latitude", 28.6139)
        self.longitude = longitude if longitude is not None else profile.get("longitude", 77.2090)
        self.aadt_calibration_factor = (
            aadt_calibration_factor
            if aadt_calibration_factor is not None
            else profile.get("aadt_calibration_factor", 37.84)
        )
        self.inventory_source = profile.get("inventory_source", "Literature Inventory Proxy")
        self.climate_zone = profile.get("climate_zone", "generic_urban")

        self.met_connector = OpenMeteoConnector()
        self.reg_connector = RegionalBackgroundConnector()
        self.overpass_connector = OverpassConnector()

    def generate_full_year(
        self,
        output_dir: Optional[Union[str, Path]] = None,
        save_artifacts: bool = True,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Generate continuous 8,760-hour simulation dataset for the specified calendar year.

        Parameters
        ----------
        output_dir : Optional[Union[str, Path]], optional
            Directory to save parquet, CSV, and metadata artifacts.
        save_artifacts : bool, default=True
            Whether to write files to disk.

        Returns
        -------
        Tuple[pd.DataFrame, Dict[str, Any]]
            Generated DataFrame and metadata provenance dictionary.
        """
        start_time = datetime(self.year, 1, 1, 0, 0, tzinfo=timezone.utc)
        # Handle leap years automatically
        is_leap = (self.year % 4 == 0 and self.year % 100 != 0) or (self.year % 400 == 0)
        n_days = 366 if is_leap else 365
        n_hours = n_days * 24
        end_time = datetime(self.year, 12, 31, 23, 0, tzinfo=timezone.utc)

        # 1. Fetch Meteorology & Regional Background
        met_ts = self.met_connector.fetch_meteorology(self.latitude, self.longitude, start_time, end_time)
        reg_ts = self.reg_connector.query(self.latitude, self.longitude, start_time, end_time)

        # 2. Extract Road Network and Configure Calibrated Line Sources
        osm_features = self.overpass_connector.fetch_features(
            min_lat=self.latitude - 0.15,
            min_lon=self.longitude - 0.15,
            max_lat=self.latitude + 0.15,
            max_lon=self.longitude + 0.15,
            include_roads=True,
            include_industrial=False,
        )
        coord = LocalCoordinateSystem(origin_lat=self.latitude, origin_lon=self.longitude)
        segments = []
        for f in osm_features:
            if f.feature_category == "road":
                segments.extend(RoadNetworkSegmenter.segment_osm_road(f, coord))

        calibrated_aadt = {k: v * self.aadt_calibration_factor for k, v in RoadEmissionConfig().aadt_by_class.items()}
        config = RoadEmissionConfig(
            aadt_by_class=calibrated_aadt,
            traffic_profile=TemporalTrafficProfile.default_indian_urban(),
        )

        src_x = np.array([s.midpoint_cartesian[0] for s in segments], dtype=np.float64)
        src_y = np.array([s.midpoint_cartesian[1] for s in segments], dtype=np.float64)
        src_len_km = np.array([s.length_meters / 1000.0 for s in segments], dtype=np.float64)
        src_ef = np.array([config.emission_factors.get(s.road_class, config.emission_factors["default"]) for s in segments], dtype=np.float64)
        src_aadt = np.array([config.aadt_by_class.get(s.road_class, config.aadt_by_class["default"]) * (0.5 if s.osm_tags.get("oneway") == "yes" else 1.0) for s in segments], dtype=np.float64)
        src_sy0 = np.maximum(5.0, np.array([s.length_meters for s in segments], dtype=np.float64) / 2.15)

        # Spatial domain radius = 15 km
        dist_to_origin = np.hypot(src_x, src_y)
        mask = dist_to_origin <= 15000.0

        src_x = src_x[mask]
        src_y = src_y[mask]
        src_len_km = src_len_km[mask]
        src_ef = src_ef[mask]
        src_aadt = src_aadt[mask]
        src_sy0 = src_sy0[mask]

        base_q = (src_len_km * src_aadt * src_ef) / 86400.0

        # 3. Simulate Hourly Dispersion Across Full Year
        rows = []
        n_records = min(len(met_ts.records), len(reg_ts.records), n_hours)

        for h in range(n_records):
            r_met = met_ts.records[h]
            r_reg = reg_ts.records[h]
            cur_dt = r_met.timestamp

            ws = r_met.wind_speed_mps
            wdir = r_met.wind_direction_deg
            temp = r_met.temperature_c
            rh = r_met.relative_humidity_pct
            # Enforce EPA / AERMOD standard minimum urban mixing height floor (50m)
            raw_pblh = r_met.boundary_layer_height_m if r_met.boundary_layer_height_m else 500.0
            pblh = max(50.0, float(raw_pblh))
            press = r_met.surface_pressure_hpa or 1013.25
            dni = r_met.direct_normal_irradiance_w_m2 or 0.0
            cloud = r_met.cloud_cover_pct or 0.0

            # Wind components (blowing towards)
            rad = np.radians(wdir)
            u_wind = -ws * np.sin(rad)
            v_wind = -ws * np.cos(rad)

            # Atmospheric stability
            stab_class = classify_stability(
                wind_speed=max(ws, 0.5),
                solar_radiation=dni,
                cloud_cover=cloud / 100.0,
                is_daytime=dni > 5.0,
            ).value

            # Local line-source dispersion
            diurnal_mult = config.traffic_profile.get_multiplier(cur_dt)
            q_vec = base_q * diurnal_mult

            ux, uy = -np.sin(rad), -np.cos(rad)
            dx, dy = -src_x, -src_y
            x_down = -(dx * ux + dy * uy)
            y_cross = np.abs(dx * uy - dy * ux)

            valid = x_down > 5.0
            if np.any(valid):
                xd = x_down[valid]
                yc = y_cross[valid]
                qv = q_vec[valid]
                sy0 = src_sy0[valid]

                sz = np.maximum(1.5, 0.06 * xd / np.sqrt(1.0 + 0.0015 * xd))
                sy = np.maximum(sy0, 0.08 * xd / np.sqrt(1.0 + 0.0001 * xd))

                u_eff = max(ws, 0.5)
                c_src = (qv / (2.0 * np.pi * u_eff * sy * sz)) * np.exp(-0.5 * (yc / sy)**2)
                if pblh > 0:
                    trap = sz > pblh
                    c_src[trap] *= (sz[trap] / pblh)

                c_local = float(np.sum(c_src)) * 1e6  # g/m3 -> ug/m3
            else:
                c_local = 0.0

            c_reg = r_reg.pm2_5_ug_m3
            c_total = c_local + c_reg

            # Quality and regime flags
            reg_meta = classify_regime_and_quality(cur_dt, city_name=self.city_name)

            # Temporal cyclic features
            hr = cur_dt.hour
            dow = cur_dt.weekday()
            mon = cur_dt.month
            is_wknd = 1 if dow >= 5 else 0
            sin_hr = math.sin(2.0 * math.pi * hr / 24.0)
            cos_hr = math.cos(2.0 * math.pi * hr / 24.0)
            sin_mon = math.sin(2.0 * math.pi * (mon - 1) / 12.0)
            cos_mon = math.cos(2.0 * math.pi * (mon - 1) / 12.0)

            sample_id = f"{self.city_name.lower()}_{self.year}_{h:04d}_{cur_dt.strftime('%Y%m%dT%H%M%SZ')}"

            rows.append({
                "sample_id": sample_id,
                "timestamp": cur_dt,
                "city": self.city_name,
                "latitude": self.latitude,
                "longitude": self.longitude,
                # Meteorology
                "wind_speed_mps": round(ws, 2),
                "wind_direction_deg": round(wdir, 1),
                "wind_u_mps": round(u_wind, 2),
                "wind_v_mps": round(v_wind, 2),
                "temperature_c": round(temp, 1),
                "relative_humidity_pct": round(rh, 1),
                "surface_pressure_hpa": round(press, 1),
                "boundary_layer_height_m": round(pblh, 1),
                "direct_normal_irradiance_w_m2": round(dni, 1),
                "cloud_cover_pct": round(cloud, 1),
                "stability_class": stab_class,
                # Temporal features
                "hour": hr,
                "day_of_week": dow,
                "month": mon,
                "is_weekend": is_wknd,
                "sin_hour": round(sin_hr, 4),
                "cos_hour": round(cos_hr, 4),
                "sin_month": round(sin_mon, 4),
                "cos_month": round(cos_mon, 4),
                # Physical targets & components
                "local_dispersion_pm25": round(c_local, 2),
                "cams_regional_pm25": round(c_reg, 2),
                "target_pm25": round(c_total, 2),
                # Quality Flags
                "regime": reg_meta.regime,
                "confidence_level": reg_meta.confidence_level,
                "known_bias_direction": reg_meta.known_bias_direction,
                "systematic_bias_note": reg_meta.systematic_bias_note,
            })

        df = pd.DataFrame(rows)

        # Build metadata summary
        meta = {
            "dataset_name": f"AtmosSim_{self.city_name}_{self.year}_Annual_Continuous",
            "version": "1.0",
            "city": self.city_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "year": self.year,
            "total_samples": len(df),
            "temporal_resolution": "1_hour",
            "start_time_utc": start_time.isoformat(),
            "end_time_utc": end_time.isoformat(),
            "road_segments_count": int(len(src_x)),
            "aadt_calibration_factor": self.aadt_calibration_factor,
            "aadt_inventory_source": "IIT Kanpur / TERI (2018) Comprehensive Delhi Study",
            "regional_background_provider": "Copernicus Atmosphere Monitoring Service (CAMS) Global Reanalysis via Open-Meteo",
            "meteorology_provider": "Open-Meteo ERA5 Historical Archive",
            "regime_distribution": df["regime"].value_counts().to_dict(),
            "confidence_level_distribution": df["confidence_level"].value_counts().to_dict(),
            "known_bias_distribution": df["known_bias_direction"].value_counts().to_dict(),
            "target_statistics": {
                "mean_pm25": round(float(df["target_pm25"].mean()), 2),
                "median_pm25": round(float(df["target_pm25"].median()), 2),
                "std_pm25": round(float(df["target_pm25"].std()), 2),
                "min_pm25": round(float(df["target_pm25"].min()), 2),
                "max_pm25": round(float(df["target_pm25"].max()), 2),
                "p25_pm25": round(float(df["target_pm25"].quantile(0.25)), 2),
                "p75_pm25": round(float(df["target_pm25"].quantile(0.75)), 2),
                "p95_pm25": round(float(df["target_pm25"].quantile(0.95)), 2),
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Save artifacts if requested
        if save_artifacts:
            target_dir = Path(output_dir or "artifacts/annual_dataset")
            target_dir.mkdir(parents=True, exist_ok=True)

            parquet_path = target_dir / f"{self.city_name.lower()}_{self.year}_annual_continuous.parquet"
            csv_path = target_dir / f"{self.city_name.lower()}_{self.year}_annual_continuous.csv"
            meta_path = target_dir / f"{self.city_name.lower()}_{self.year}_annual_metadata.json"

            df.to_parquet(parquet_path, index=False)
            df.to_csv(csv_path, index=False)
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)

            meta["artifacts"] = {
                "parquet_file": str(parquet_path),
                "csv_file": str(csv_path),
                "metadata_file": str(meta_path),
            }

        return df, meta
