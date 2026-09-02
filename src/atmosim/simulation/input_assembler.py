"""
General-Location Simulation Input Assembly Engine for AtmosSim.

Transforms a geographic coordinate (latitude, longitude) and date range into
a fully validated, provenance-complete SimulationInput object ready for the
Phase 1 Gaussian Puff engine.

Architecture
------------
(lat, lon, date_range)
         │
         ▼
  Domain Resolver & Coordinate Frame Setup
         │
 ┌───────┼────────────────────────┐
 ▼       ▼                        ▼
Open-   Terrain              Overpass / OSM
Meteo   Grid                 Road & Industrial Proxies
 │       │                        │
 ▼       ▼                        ▼
Normalized Continuous        Segmented Sources &
Meteorological Time Series   Proxy-to-Emission Q(t)
 └───────┬────────────────────────┘
         ▼
  Spatial Alignment & Validation QA
         │
         ▼
  Complete SimulationInput with Machine-Readable Manifest
         │
         ▼
  Phase 1 Gaussian Puff Engine
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
import hashlib
import json
import math
import numpy as np

from atmosim.data.cache import DataCache
from atmosim.data.open_meteo import (
    MeteorologicalTimeSeries,
    OpenMeteoConnector,
)
from atmosim.data.overpass import (
    RawOsmFeature,
    OverpassConnector,
)
from atmosim.data.terrain import (
    TerrainField,
    TerrainConnector,
)
from atmosim.physics.coordinates import LocalCoordinateSystem
from atmosim.physics.puff import (
    EmissionSource,
    GaussianPuffConfig,
    GaussianPuffEngine,
    WindField,
)
from atmosim.physics.puff_lifecycle import (
    PuffLifecycleConfig,
    SpatialBounds,
)
from atmosim.sources.emissions import (
    ProxyEmissionParameterizer,
    RoadEmissionConfig,
    RoadNetworkSegmenter,
)
from atmosim.sources.models import (
    IndustrialProxy,
    PointSourceProxy,
    RoadSegmentProxy,
)
from atmosim.sources.provenance import (
    SourceProvenance,
    UncertaintyClass,
)


@dataclass
class SimulationInput:
    """
    Assembled, validated simulation inputs consumable by the Phase 1 Gaussian Puff engine.
    """
    coordinate_system: LocalCoordinateSystem
    meteorology: MeteorologicalTimeSeries
    terrain: TerrainField
    sources: List[EmissionSource]
    road_segments: List[RoadSegmentProxy]
    industrial_proxies: List[IndustrialProxy]
    point_sources: List[PointSourceProxy]
    source_provenance: Dict[str, SourceProvenance]
    domain_radius_m: float
    start_time: datetime
    end_time: datetime
    input_manifest: Dict[str, Any]
    input_hash: str

    @property
    def duration_seconds(self) -> float:
        """Total duration of simulation window in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    @property
    def domain_bounds_m(self) -> Tuple[float, float, float, float]:
        """(x_min, x_max, y_min, y_max) in meters."""
        r = self.domain_radius_m
        return (-r, r, -r, r)

    def to_puff_engine(
        self,
        config: Optional[GaussianPuffConfig] = None,
        lifecycle_config: Optional[PuffLifecycleConfig] = None,
    ) -> GaussianPuffEngine:
        """
        Initialize a Phase 1 GaussianPuffEngine populated with assembled sources and wind field.
        """
        # Configure lifecycle bounds matching domain radius with margin
        if lifecycle_config is None:
            r = self.domain_radius_m * 1.5
            bounds = SpatialBounds(
                x_min=-r, x_max=r,
                y_min=-r, y_max=r,
                z_min=0.0, z_max=2000.0,
            )
            lifecycle_config = PuffLifecycleConfig(
                max_age=max(3600.0, self.duration_seconds),
                max_distance=r,
                bounds=bounds,
            )

        if config is None:
            engine_config = GaussianPuffConfig(time_step=1.0, lifecycle_config=lifecycle_config)
        else:
            engine_config = GaussianPuffConfig(
                time_step=config.time_step,
                stability=config.stability,
                environment=config.environment,
                calm_wind_threshold=config.calm_wind_threshold,
                include_ground_reflection=config.include_ground_reflection,
                mass_decay_rate=config.mass_decay_rate,
                lifecycle_config=lifecycle_config,
            )

        engine = GaussianPuffEngine(config=engine_config)

        for src in self.sources:
            engine.add_source(src)

        return engine

    def get_wind_field(self) -> WindField:
        """Build Phase 1 WindField from assembled continuous meteorology."""
        return self.meteorology.to_wind_field()


class SimulationInputAssembler:
    """
    Orchestrates ingestion, normalization, parameterization, and assembly of simulation inputs.
    """

    def __init__(
        self,
        cache: Optional[DataCache] = None,
        meteo_connector: Optional[OpenMeteoConnector] = None,
        terrain_connector: Optional[TerrainConnector] = None,
        overpass_connector: Optional[OverpassConnector] = None,
        road_config: Optional[RoadEmissionConfig] = None,
    ) -> None:
        self.cache = cache if cache is not None else DataCache()
        self.meteo_connector = meteo_connector or OpenMeteoConnector(cache=self.cache)
        self.terrain_connector = terrain_connector or TerrainConnector(cache=self.cache)
        self.overpass_connector = overpass_connector or OverpassConnector(cache=self.cache)
        self.road_config = road_config or RoadEmissionConfig()
        self.emission_parameterizer = ProxyEmissionParameterizer(config=self.road_config)

    def build(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
        domain_radius_m: float = 3000.0,
        terrain_resolution_m: float = 500.0,
        max_segment_length_m: float = 250.0,
        allow_synthetic_sources_on_empty: bool = True,
    ) -> SimulationInput:
        """
        Assemble complete simulation inputs for specified geographic coordinates and date range.

        Parameters
        ----------
        latitude : float
            Simulation domain anchor latitude (-90 to 90).
        longitude : float
            Simulation domain anchor longitude (-180 to 180).
        start_time : datetime
            Simulation window start timestamp.
        end_time : datetime
            Simulation window end timestamp.
        domain_radius_m : float, default=3000.0
            Half-width of simulation domain in meters.
        terrain_resolution_m : float, default=500.0
            Resolution of digital elevation grid in meters.
        max_segment_length_m : float, default=250.0
            Maximum length of a discrete linear road segment source.
        allow_synthetic_sources_on_empty : bool, default=True
            If True and OSM returns 0 features, creates standard synthetic road proxy.

        Returns
        -------
        SimulationInput
            Fully assembled, validated simulation inputs.
        """
        # 1. Validate inputs
        if not (-90.0 <= latitude <= 90.0):
            raise ValueError(f"Latitude out of bounds [-90, 90]: {latitude}")
        if not (-180.0 <= longitude <= 180.0):
            raise ValueError(f"Longitude out of bounds [-180, 180]: {longitude}")

        start_utc = start_time if start_time.tzinfo else start_time.replace(tzinfo=timezone.utc)
        end_utc = end_time if end_time.tzinfo else end_time.replace(tzinfo=timezone.utc)

        if start_utc >= end_utc:
            raise ValueError(f"start_time ({start_utc}) must be strictly before end_time ({end_utc})")
        if domain_radius_m <= 0:
            raise ValueError(f"domain_radius_m must be strictly positive, got {domain_radius_m}")

        # 2. Canonical Coordinate System
        coord_system = LocalCoordinateSystem(origin_lat=latitude, origin_lon=longitude)

        # 3. Calculate Geodetic Bounding Box
        # ~111,320 meters per degree latitude; approx cos(lat) for longitude
        lat_delta = (domain_radius_m * 1.1) / 111320.0
        cos_lat = max(0.01, math.cos(math.radians(latitude)))
        lon_delta = (domain_radius_m * 1.1) / (111320.0 * cos_lat)

        min_lat = max(-90.0, latitude - lat_delta)
        max_lat = min(90.0, latitude + lat_delta)
        min_lon = max(-180.0, longitude - lon_delta)
        max_lon = min(180.0, longitude + lon_delta)

        # 4. Ingest Meteorology
        meteorology = self.meteo_connector.fetch_meteorology(
            latitude=latitude,
            longitude=longitude,
            start_time=start_utc,
            end_time=end_utc,
        )

        # 5. Ingest Terrain Elevation
        terrain = self.terrain_connector.fetch_elevation_grid(
            coordinate_system=coord_system,
            domain_radius_m=domain_radius_m,
            resolution_m=terrain_resolution_m,
        )

        # 6. Ingest OSM Geographic Source Proxies
        osm_features = self.overpass_connector.fetch_features(
            min_lat=min_lat,
            min_lon=min_lon,
            max_lat=max_lat,
            max_lon=max_lon,
            include_roads=True,
            include_industrial=True,
        )

        # 7. Segment Roads and Parameterize Emissions
        road_segments: List[RoadSegmentProxy] = []
        industrial_proxies: List[IndustrialProxy] = []
        point_sources: List[PointSourceProxy] = []

        sources: List[EmissionSource] = []
        source_provenance: Dict[str, SourceProvenance] = {}

        for feat in osm_features:
            if feat.feature_category == "road":
                segs = RoadNetworkSegmenter.segment_osm_road(
                    feature=feat,
                    coord_system=coord_system,
                    max_segment_len_m=max_segment_length_m,
                )
                for seg in segs:
                    # Check if within domain bounds
                    mx, my = seg.midpoint_cartesian
                    if abs(mx) <= domain_radius_m and abs(my) <= domain_radius_m:
                        road_segments.append(seg)
                        src_obj, prov = self.emission_parameterizer.create_road_emission_source(
                            segment=seg,
                            simulation_start=start_utc,
                            release_interval=10.0,
                        )
                        sources.append(src_obj)
                        source_provenance[seg.segment_id] = prov

            elif feat.feature_category == "industrial":
                if feat.osm_type == "node" and feat.geometry:
                    lat_i, lon_i = feat.geometry[0]
                    xi, yi = coord_system.geo_to_cartesian(lat_i, lon_i)
                    p_proxy = PointSourceProxy(
                        proxy_id=f"osm_ind_pt_{feat.osm_id}",
                        osm_id=feat.osm_id,
                        location_geo=(lat_i, lon_i),
                        location_cartesian=(float(xi), float(yi)),
                        estimated_height_m=20.0,
                        osm_tags=feat.tags,
                    )
                    point_sources.append(p_proxy)
                elif feat.osm_type == "way" and len(feat.geometry) >= 3:
                    lats = [p[0] for p in feat.geometry]
                    lons = [p[1] for p in feat.geometry]
                    clat, clon = float(np.mean(lats)), float(np.mean(lons))
                    cx, cy = coord_system.geo_to_cartesian(clat, clon)
                    ind_proxy = IndustrialProxy(
                        proxy_id=f"osm_ind_poly_{feat.osm_id}",
                        osm_id=feat.osm_id,
                        area_m2=10000.0,  # Approximate footprint
                        centroid_geo=(clat, clon),
                        centroid_cartesian=(float(cx), float(cy)),
                        osm_tags=feat.tags,
                        emission_status="unavailable",
                    )
                    industrial_proxies.append(ind_proxy)

        # Fallback synthetic road source if no OSM features found
        if not sources and allow_synthetic_sources_on_empty:
            synth_feat = RawOsmFeature(
                osm_type="way",
                osm_id=999901,
                tags={"highway": "primary", "name": "Synthetic Arterial Corridor"},
                geometry=[(latitude - 0.005, longitude), (latitude + 0.005, longitude)],
                feature_category="road",
            )
            segs = RoadNetworkSegmenter.segment_osm_road(
                feature=synth_feat,
                coord_system=coord_system,
                max_segment_len_m=max_segment_length_m,
            )
            for seg in segs:
                road_segments.append(seg)
                src_obj, prov = self.emission_parameterizer.create_road_emission_source(
                    segment=seg,
                    simulation_start=start_utc,
                    release_interval=10.0,
                )
                sources.append(src_obj)
                source_provenance[seg.segment_id] = prov

        # 8. Construct Input Manifest
        manifest = {
            "version": "AtmosSim_Phase2_v1.0",
            "assembled_at_utc": datetime.now(timezone.utc).isoformat(),
            "domain": {
                "latitude": latitude,
                "longitude": longitude,
                "domain_radius_m": domain_radius_m,
                "crs_epsg": coord_system.crs_epsg,
            },
            "temporal_window": {
                "start_time_utc": start_utc.isoformat(),
                "end_time_utc": end_utc.isoformat(),
                "duration_seconds": (end_utc - start_utc).total_seconds(),
            },
            "meteorology_provenance": meteorology.provenance,
            "terrain_provenance": terrain.provenance,
            "sources_summary": {
                "total_active_emission_sources": len(sources),
                "total_road_segments": len(road_segments),
                "total_industrial_proxies": len(industrial_proxies),
                "total_point_sources": len(point_sources),
                "pollutant": self.road_config.pollutant,
            },
        }

        # 9. Deterministic Fingerprint Hash
        manifest_serialized = json.dumps(manifest, sort_keys=True, default=str)
        input_hash = hashlib.sha256(manifest_serialized.encode("utf-8")).hexdigest()

        return SimulationInput(
            coordinate_system=coord_system,
            meteorology=meteorology,
            terrain=terrain,
            sources=sources,
            road_segments=road_segments,
            industrial_proxies=industrial_proxies,
            point_sources=point_sources,
            source_provenance=source_provenance,
            domain_radius_m=domain_radius_m,
            start_time=start_utc,
            end_time=end_utc,
            input_manifest=manifest,
            input_hash=input_hash,
        )
