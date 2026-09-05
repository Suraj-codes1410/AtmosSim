"""
Proxy-to-Emission Parameterization Engine for AtmosSim.

Transforms OpenStreetMap road network geometries, classifications, and industrial proxies
into time-dependent pollutant emission rates Q(t) [g/s] with full scientific provenance.

Mathematical Formulation
------------------------
For a discrete road segment of length L [meters]:
1. Geodesic / Cartesian road length in kilometers:
   L_km = L_meters / 1000.0  [km]

2. Hourly traffic activity:
   V(t) = AADT_class * (f(t) / 24.0)  [vehicles / hour]
   where AADT_class is the assumed proxy traffic count for the road classification,
   and f(t) is the normalized diurnal multiplier ((1/24) * sum(f_h) = 1.0).

3. Instantaneous PM2.5 emission rate:
   Q_road(t) = L_km * V(t) * EF * (1.0 / 3600.0)  [g/s]
   where EF is the composite fleet PM2.5 emission factor in [g / vehicle-km].

Dimensional Verification:
[km] * [vehicles / hour] * [g / (vehicle * km)] * [1 hour / 3600 s] = [g / s]
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
import math
import numpy as np

from atmosim.data.overpass import RawOsmFeature
from atmosim.physics.coordinates import LocalCoordinateSystem
from atmosim.physics.puff import EmissionSource
from atmosim.sources.models import (
    ProxyType,
    RoadSegmentProxy,
    IndustrialProxy,
    PointSourceProxy,
)
from atmosim.sources.provenance import SourceProvenance, UncertaintyClass
from atmosim.sources.traffic_profiles import TemporalTrafficProfile


# Literature-derived composite emission factors [g PM2.5 / vehicle-km]
# Sources: EMEP/EEA Emission Inventory Guidebook (2019); CPCB / ARAI Indian Fleet Estimates (2018)
DEFAULT_EMISSION_FACTORS: Dict[str, float] = {
    "motorway": 0.22,      # High-speed exhaust + non-exhaust brake/tire wear
    "trunk": 0.18,
    "primary": 0.14,
    "secondary": 0.10,
    "tertiary": 0.08,
    "residential": 0.05,
    "service": 0.03,
    "unclassified": 0.05,
    "default": 0.10,
}

# Proxy Annual Average Daily Traffic (AADT) volume defaults [vehicles / day]
DEFAULT_AADT_BY_CLASS: Dict[str, float] = {
    "motorway": 45000.0,
    "trunk": 30000.0,
    "primary": 20000.0,
    "secondary": 10000.0,
    "tertiary": 4000.0,
    "residential": 1200.0,
    "service": 400.0,
    "unclassified": 800.0,
    "default": 2000.0,
}


@dataclass
class RoadEmissionConfig:
    """
    Configuration parameters for proxy road emission estimation.
    """
    pollutant: str = "PM2.5"
    emission_factors: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_EMISSION_FACTORS))
    aadt_by_class: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_AADT_BY_CLASS))
    traffic_profile: TemporalTrafficProfile = field(default_factory=TemporalTrafficProfile.default_urban_diurnal)
    max_segment_length_m: float = 250.0  # Maximum length of a single discrete road segment source
    release_height_m: float = 0.5  # Ground-level tailpipe & brake wear release height in meters
    initial_sigma: Tuple[float, float, float] = (5.0, 5.0, 1.5)  # Initial road volume dispersion spread
    emission_factor_source: str = "EMEP/EEA (2019) & CPCB/ARAI (2018) Urban Fleet PM2.5 Composite"


class RoadNetworkSegmenter:
    """
    Segments OSM road vector ways into discrete, spatially bounded RoadSegmentProxy elements.
    """

    @staticmethod
    def segment_osm_road(
        feature: RawOsmFeature,
        coord_system: LocalCoordinateSystem,
        max_segment_len_m: float = 250.0,
    ) -> List[RoadSegmentProxy]:
        """
        Segment a multi-point OSM road polyline into discrete linear segments.

        Parameters
        ----------
        feature : RawOsmFeature
            OSM road way feature with geometry.
        coord_system : LocalCoordinateSystem
            Simulation coordinate system.
        max_segment_len_m : float, default=250.0
            Maximum length of a discrete segment in meters.

        Returns
        -------
        List[RoadSegmentProxy]
            Discrete road segment proxies.
        """
        if len(feature.geometry) < 2:
            return []

        road_class = feature.tags.get("highway", "default").lower()
        if road_class not in DEFAULT_EMISSION_FACTORS:
            road_class = "default"

        # Project all nodes to local Cartesian (x, y) meters
        coords_geo = feature.geometry
        coords_xy: List[Tuple[float, float]] = []
        for lat, lon in coords_geo:
            x, y = coord_system.geo_to_cartesian(lat, lon)
            coords_xy.append((float(x), float(y)))

        segments: List[RoadSegmentProxy] = []
        seg_idx = 0

        # Traverse sequential polyline vertices
        for i in range(len(coords_xy) - 1):
            p1_geo, p2_geo = coords_geo[i], coords_geo[i + 1]
            p1_xy, p2_xy = coords_xy[i], coords_xy[i + 1]

            dx = p2_xy[0] - p1_xy[0]
            dy = p2_xy[1] - p1_xy[1]
            sub_len = math.sqrt(dx * dx + dy * dy)

            if sub_len <= 1e-3:
                continue

            # Subdivide if length exceeds max_segment_len_m
            num_sub = max(1, math.ceil(sub_len / max_segment_len_m))
            for k in range(num_sub):
                f0 = k / num_sub
                f1 = (k + 1) / num_sub
                f_mid = 0.5 * (f0 + f1)

                seg_len = sub_len / num_sub

                # Interpolated Cartesian coordinates
                s_xy = (p1_xy[0] + f0 * dx, p1_xy[1] + f0 * dy)
                e_xy = (p1_xy[0] + f1 * dx, p1_xy[1] + f1 * dy)
                mid_xy = (p1_xy[0] + f_mid * dx, p1_xy[1] + f_mid * dy)

                # Interpolated Geographic coordinates
                s_geo = (p1_geo[0] + f0 * (p2_geo[0] - p1_geo[0]), p1_geo[1] + f0 * (p2_geo[1] - p1_geo[1]))
                e_geo = (p1_geo[0] + f1 * (p2_geo[0] - p1_geo[0]), p1_geo[1] + f1 * (p2_geo[1] - p1_geo[1]))
                mid_geo = (p1_geo[0] + f_mid * (p2_geo[0] - p1_geo[0]), p1_geo[1] + f_mid * (p2_geo[1] - p1_geo[1]))

                segment_id = f"osm_road_{feature.osm_id}_seg{seg_idx}"
                seg_idx += 1

                segments.append(
                    RoadSegmentProxy(
                        segment_id=segment_id,
                        parent_osm_id=feature.osm_id,
                        road_class=road_class,
                        length_meters=float(seg_len),
                        start_point_geo=s_geo,
                        end_point_geo=e_geo,
                        midpoint_geo=mid_geo,
                        midpoint_cartesian=mid_xy,
                        osm_tags=feature.tags,
                    )
                )

        return segments


class ProxyEmissionParameterizer:
    """
    Parameterizes source proxies into time-dependent PM2.5 emissions Q(t) and Phase 1 EmissionSource instances.
    """

    def __init__(self, config: Optional[RoadEmissionConfig] = None) -> None:
        self.config = config if config is not None else RoadEmissionConfig()

    def compute_road_segment_emission_rate(
        self,
        segment: RoadSegmentProxy,
        timestamp: datetime,
    ) -> float:
        """
        Compute instantaneous PM2.5 emission rate Q [g/s] for a single road segment at given timestamp.

        Parameters
        ----------
        segment : RoadSegmentProxy
            Road segment proxy.
        timestamp : datetime
            Observation timestamp for diurnal activity evaluation.

        Returns
        -------
        float
            Emission rate Q in grams per second [g/s].
        """
        road_class = segment.road_class
        ef = self.config.emission_factors.get(road_class, self.config.emission_factors["default"])
        aadt = self.config.aadt_by_class.get(road_class, self.config.aadt_by_class["default"])

        # Oneway dual-carriageway correction: if oneway=yes, directional traffic is half of 2-way AADT
        if segment.osm_tags.get("oneway") == "yes":
            aadt *= 0.5

        activity_mult = self.config.traffic_profile.get_multiplier(timestamp)

        # 1. Length in kilometers
        length_km = segment.length_meters / 1000.0

        # 2. Vehicles per hour
        v_hourly = aadt * (activity_mult / 24.0)

        # 3. Emission rate in g/s: (km * veh/hr * g/(veh*km)) / 3600 s/hr
        q_gps = (length_km * v_hourly * ef) / 3600.0

        return float(q_gps)

    def create_road_emission_source(
        self,
        segment: RoadSegmentProxy,
        simulation_start: datetime,
        release_interval: float = 10.0,
    ) -> Tuple[EmissionSource, SourceProvenance]:
        """
        Create a Phase 1 EmissionSource and corresponding SourceProvenance for a road segment.
        """
        q0 = self.compute_road_segment_emission_rate(segment, simulation_start)
        mx, my = segment.midpoint_cartesian

        # Callable time-varying emission rate Q(t)
        def q_func(t_seconds: float) -> float:
            current_time = simulation_start.timestamp() + t_seconds
            dt = datetime.fromtimestamp(current_time, tz=timezone.utc)
            return self.compute_road_segment_emission_rate(segment, dt)

        # EPA CALINE4 / ISC3 line-source volume representation: initial sigma scales with segment length
        L = segment.length_meters
        sx0 = max(5.0, L / 2.15)
        sy0 = max(5.0, 12.0 / 2.15)
        sz0 = max(1.5, 3.5 / 2.15)

        emission_source = EmissionSource(
            source_id=segment.segment_id,
            x=mx,
            y=my,
            z=self.config.release_height_m,
            emission_rate=q_func,
            release_interval=release_interval,
            initial_sigma=(sx0, sy0, sz0),
        )

        ef_val = self.config.emission_factors.get(segment.road_class, self.config.emission_factors["default"])

        provenance = SourceProvenance(
            source_id=segment.segment_id,
            proxy_type=ProxyType.ROAD_SEGMENT.value,
            proxy_provider="OpenStreetMap",
            proxy_id=str(segment.parent_osm_id),
            pollutant=self.config.pollutant,
            emission_method="RoadProxy_Length_x_AADT_x_EF_x_DiurnalActivity",
            emission_factor=ef_val,
            emission_factor_units="g PM2.5 / vehicle-km",
            emission_factor_source=self.config.emission_factor_source,
            activity_profile=self.config.traffic_profile.profile_name,
            activity_profile_source=self.config.traffic_profile.source_reference,
            uncertainty_class=UncertaintyClass.HIGH,
            retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
            assumptions=[
                f"AADT proxy count {self.config.aadt_by_class.get(segment.road_class, 'default')} veh/day for highway={segment.road_class}",
                f"Diurnal activity profile {self.config.traffic_profile.profile_name}",
                f"Ground-level line source discretized to point midpoint at z={self.config.release_height_m}m",
                "Unmeasured proxy parameterization (UncertaintyClass: HIGH)",
            ],
        )

        return emission_source, provenance
