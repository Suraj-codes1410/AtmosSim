"""
OpenStreetMap Overpass API Source Proxy Ingestion Module for AtmosSim.

Retrieves geographic road network geometries, industrial land-use footprints,
and industrial point-source features within a spatially bounded simulation domain.

Important Scientific Qualification
-----------------------------------
OpenStreetMap provides geographic proxy geometries, tags, and classifications.
It does NOT provide physical emission rates or measured traffic volumes.
All emissions derived from OSM objects are proxy parameterizations with explicit uncertainty.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import requests

from atmosim.data.cache import DataCache


@dataclass
class RawOsmFeature:
    """Raw parsed OpenStreetMap vector geometry feature."""
    osm_type: str  # 'node', 'way', 'relation'
    osm_id: int
    tags: Dict[str, str]
    geometry: List[Tuple[float, float]]  # List of (latitude, longitude) pairs
    feature_category: str  # 'road', 'industrial', 'point_source'


class OverpassConnector:
    """
    Client for querying OpenStreetMap features via the Overpass API.

    Parameters
    ----------
    endpoint : str, default='https://overpass-api.de/api/interpreter'
        Overpass API endpoint URL.
    cache : Optional[DataCache], optional
        Data cache manager.
    timeout_seconds : float, default=25.0
        Request timeout in seconds.
    max_retries : int, default=3
        Maximum retry attempts on network error.
    """

    DEFAULT_ENDPOINT = "https://overpass-api.de/api/interpreter"

    def __init__(
        self,
        endpoint: Optional[str] = None,
        cache: Optional[DataCache] = None,
        timeout_seconds: float = 25.0,
        max_retries: int = 3,
    ) -> None:
        self.endpoint = endpoint if endpoint is not None else self.DEFAULT_ENDPOINT
        self.cache = cache if cache is not None else DataCache()
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    @staticmethod
    def build_query(
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        include_roads: bool = True,
        include_industrial: bool = True,
    ) -> str:
        """
        Construct a structured, spatially bounded Overpass QL query string.

        Parameters
        ----------
        min_lat, min_lon, max_lat, max_lon : float
            Geographic bounding box coordinates in decimal degrees.
        include_roads : bool, default=True
            Query road ways with highway=* tags.
        include_industrial : bool, default=True
            Query industrial polygons and point tags.

        Returns
        -------
        str
            Overpass QL query string.
        """
        bbox_str = f"{min_lat:.5f},{min_lon:.5f},{max_lat:.5f},{max_lon:.5f}"
        clauses = []

        if include_roads:
            clauses.append(f'way["highway"~"motorway|trunk|primary|secondary|tertiary|residential|service|unclassified"]({bbox_str});')

        if include_industrial:
            clauses.append(f'way["landuse"="industrial"]({bbox_str});')
            clauses.append(f'relation["landuse"="industrial"]({bbox_str});')
            clauses.append(f'node["man_made"~"chimney|works"]({bbox_str});')
            clauses.append(f'node["power"="generator"]({bbox_str});')

        joined_clauses = "\n  ".join(clauses)
        query = f"""
[out:json][timeout:25];
(
  {joined_clauses}
);
out body;
>;
out skel qt;
"""
        return query.strip()

    def fetch_features(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        include_roads: bool = True,
        include_industrial: bool = True,
    ) -> List[RawOsmFeature]:
        """
        Execute bounded Overpass query and parse results into normalized RawOsmFeature list.
        """
        query = self.build_query(
            min_lat=min_lat,
            min_lon=min_lon,
            max_lat=max_lat,
            max_lon=max_lon,
            include_roads=include_roads,
            include_industrial=include_industrial,
        )

        cache_key = self.cache.generate_key("overpass", {
            "bbox": [min_lat, min_lon, max_lat, max_lon],
            "roads": include_roads,
            "industrial": include_industrial,
        })

        raw_json = self.cache.get(cache_key)
        if raw_json is None:
            try:
                resp = requests.post(
                    self.endpoint,
                    data={"data": query},
                    timeout=self.timeout_seconds,
                    headers={"User-Agent": "AtmosSim-Dispersion-Research/0.2.0"},
                )
                resp.raise_for_status()
                raw_json = resp.json()
                self.cache.set(cache_key, raw_json)
            except Exception as exc:
                raise RuntimeError(
                    f"Overpass API query failed at {self.endpoint}: {exc}"
                ) from exc

        return self.parse_response(raw_json)

    @staticmethod
    def parse_response(raw_json: Dict[str, Any]) -> List[RawOsmFeature]:
        """
        Parse raw Overpass JSON elements into structured RawOsmFeature objects.
        """
        if "elements" not in raw_json:
            return []

        elements = raw_json["elements"]

        # 1. Map all nodes by ID: id -> (lat, lon)
        nodes: Dict[int, Tuple[float, float]] = {}
        for el in elements:
            if el.get("type") == "node" and "lat" in el and "lon" in el:
                nodes[el["id"]] = (float(el["lat"]), float(el["lon"]))

        features: List[RawOsmFeature] = []

        # 2. Parse ways and point nodes with tags
        for el in elements:
            el_type = el.get("type")
            el_id = el.get("id")
            tags = el.get("tags", {})

            if not tags:
                continue

            # Check category
            if "highway" in tags:
                category = "road"
            elif tags.get("landuse") == "industrial" or "man_made" in tags or "power" in tags:
                category = "industrial"
            else:
                category = "other"

            if el_type == "way" and "nodes" in el:
                geom = [nodes[nid] for nid in el["nodes"] if nid in nodes]
                if len(geom) >= 2:
                    features.append(
                        RawOsmFeature(
                            osm_type="way",
                            osm_id=el_id,
                            tags=tags,
                            geometry=geom,
                            feature_category=category,
                        )
                    )
            elif el_type == "node" and el_id in nodes:
                features.append(
                    RawOsmFeature(
                        osm_type="node",
                        osm_id=el_id,
                        tags=tags,
                        geometry=[nodes[el_id]],
                        feature_category=category,
                    )
                )

        return features
