"""
Normalized Source Proxy Data Models for AtmosSim.

Defines spatial source proxies extracted from geographic databases (OpenStreetMap/Overpass),
including road segments, industrial footprints, and point sources.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ProxyType(str, Enum):
    """Classification of geographic source proxy entity."""
    ROAD_SEGMENT = "ROAD_SEGMENT"
    INDUSTRIAL_POLYGON = "INDUSTRIAL_POLYGON"
    POINT_SOURCE = "POINT_SOURCE"


@dataclass
class RoadSegmentProxy:
    """
    Spatially discrete linear road segment source element.

    Parameters
    ----------
    segment_id : str
        Unique identifier for the discrete road segment.
    parent_osm_id : int
        OpenStreetMap way ID from which this segment was derived.
    road_class : str
        OSM highway classification ('motorway', 'primary', 'secondary', etc.).
    length_meters : float
        Calculated physical geodesic length in metric Cartesian meters.
    start_point_geo : Tuple[float, float]
        (latitude, longitude) of segment start point.
    end_point_geo : Tuple[float, float]
        (latitude, longitude) of segment end point.
    midpoint_geo : Tuple[float, float]
        (latitude, longitude) of segment midpoint.
    midpoint_cartesian : Tuple[float, float]
        (x, y) in meters relative to local simulation origin (+x=East, +y=North).
    osm_tags : Dict[str, str]
        Original OSM key-value tags.
    """
    segment_id: str
    parent_osm_id: int
    road_class: str
    length_meters: float
    start_point_geo: Tuple[float, float]
    end_point_geo: Tuple[float, float]
    midpoint_geo: Tuple[float, float]
    midpoint_cartesian: Tuple[float, float]
    osm_tags: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if self.length_meters <= 0.0:
            raise ValueError(f"Road segment length must be strictly positive, got {self.length_meters}")


@dataclass
class IndustrialProxy:
    """
    Industrial area or facility land-use proxy.
    """
    proxy_id: str
    osm_id: int
    area_m2: float
    centroid_geo: Tuple[float, float]
    centroid_cartesian: Tuple[float, float]
    osm_tags: Dict[str, str] = field(default_factory=dict)
    emission_status: str = "unavailable"  # 'estimated' or 'unavailable'


@dataclass
class PointSourceProxy:
    """
    Discrete point source proxy (e.g. chimney, power generator).
    """
    proxy_id: str
    osm_id: int
    location_geo: Tuple[float, float]
    location_cartesian: Tuple[float, float]
    estimated_height_m: float = 20.0
    osm_tags: Dict[str, str] = field(default_factory=dict)
