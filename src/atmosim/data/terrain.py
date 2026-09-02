"""
Terrain and Elevation Ingestion Module for AtmosSim.

Provides gridded digital elevation model (DEM) ingestion, spatial interpolation
(bilinear and nearest-neighbor), coordinate transformation alignment, and domain coverage checks.

Important Scientific Qualification
-----------------------------------
This module provides geometric terrain surface elevation z_terrain(x, y).
Ingestion of terrain elevation does NOT constitute terrain-aware atmospheric flow dynamics
(e.g., wind deflection, valley channeling, or mountain-wave turbulence).
Dynamic terrain-flow coupling requires diagnostic flow modeling (scheduled for Phase 3).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import math
import numpy as np
import requests

from atmosim.data.cache import DataCache
from atmosim.physics.coordinates import LocalCoordinateSystem


@dataclass
class TerrainField:
    """
    Continuous 2D digital elevation model (DEM) surface over simulation domain.

    Parameters
    ----------
    coordinate_system : LocalCoordinateSystem
        Anchor coordinate system mapping local metric Cartesian (x, y) to (lat, lon).
    x_coords : np.ndarray
        1D array of strictly increasing Eastward metric coordinates in meters.
    y_coords : np.ndarray
        1D array of strictly increasing Northward metric coordinates in meters.
    elevation_grid : np.ndarray
        2D grid of surface elevations in meters above sea level (shape: [len(y_coords), len(x_coords)]).
    provenance : Dict[str, Any]
        Metadata tracking provider, resolution, retrieval timestamp, and interpolation method.
    """
    coordinate_system: LocalCoordinateSystem
    x_coords: np.ndarray
    y_coords: np.ndarray
    elevation_grid: np.ndarray
    provenance: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.x_coords = np.asanyarray(self.x_coords, dtype=np.float64)
        self.y_coords = np.asanyarray(self.y_coords, dtype=np.float64)
        self.elevation_grid = np.asanyarray(self.elevation_grid, dtype=np.float64)

        if self.elevation_grid.shape != (len(self.y_coords), len(self.x_coords)):
            raise ValueError(
                f"elevation_grid shape {self.elevation_grid.shape} must match "
                f"(len(y_coords), len(x_coords)) = ({len(self.y_coords)}, {len(self.x_coords)})"
            )
        if len(self.x_coords) < 2 or len(self.y_coords) < 2:
            raise ValueError("TerrainField grid must have at least 2 points in each dimension.")
        if np.any(np.diff(self.x_coords) <= 0) or np.any(np.diff(self.y_coords) <= 0):
            raise ValueError("x_coords and y_coords must be strictly monotonically increasing.")

    @property
    def bounds_cartesian(self) -> Tuple[float, float, float, float]:
        """(x_min, x_max, y_min, y_max) in meters."""
        return (
            float(self.x_coords[0]),
            float(self.x_coords[-1]),
            float(self.y_coords[0]),
            float(self.y_coords[-1]),
        )

    def get_elevation_cartesian(
        self,
        x: Union[float, np.ndarray],
        y: Union[float, np.ndarray],
        method: str = "bilinear",
    ) -> Union[float, np.ndarray]:
        """
        Query ground surface elevation at local Cartesian coordinate(s) (x, y) in meters.

        Parameters
        ----------
        x : float or np.ndarray
            Eastward coordinate(s) in meters.
        y : float or np.ndarray
            Northward coordinate(s) in meters.
        method : str, default='bilinear'
            Interpolation method: 'bilinear' or 'nearest'.

        Returns
        -------
        float or np.ndarray
            Surface elevation in meters above sea level.
        """
        is_scalar = np.isscalar(x) and np.isscalar(y)
        x_arr = np.asanyarray(x, dtype=np.float64)
        y_arr = np.asanyarray(y, dtype=np.float64)

        x_min, x_max, y_min, y_max = self.bounds_cartesian

        if np.any((x_arr < x_min) | (x_arr > x_max) | (y_arr < y_min) | (y_arr > y_max)):
            raise ValueError(
                f"Coordinates out of terrain coverage bounds: x in [{x_min}, {x_max}], y in [{y_min}, {y_max}]."
            )

        dx = self.x_coords[1] - self.x_coords[0]
        dy = self.y_coords[1] - self.y_coords[0]

        if method == "nearest":
            ix = np.clip(np.round((x_arr - x_min) / dx).astype(int), 0, len(self.x_coords) - 1)
            iy = np.clip(np.round((y_arr - y_min) / dy).astype(int), 0, len(self.y_coords) - 1)
            elev = self.elevation_grid[iy, ix]
        elif method == "bilinear":
            # Fractional indices
            gx = (x_arr - x_min) / dx
            gy = (y_arr - y_min) / dy

            x0 = np.clip(np.floor(gx).astype(int), 0, len(self.x_coords) - 2)
            x1 = x0 + 1
            y0 = np.clip(np.floor(gy).astype(int), 0, len(self.y_coords) - 2)
            y1 = y0 + 1

            wx = gx - x0
            wy = gy - y0

            z00 = self.elevation_grid[y0, x0]
            z01 = self.elevation_grid[y0, x1]
            z10 = self.elevation_grid[y1, x0]
            z11 = self.elevation_grid[y1, x1]

            elev = (
                (1.0 - wx) * (1.0 - wy) * z00
                + wx * (1.0 - wy) * z01
                + (1.0 - wx) * wy * z10
                + wx * wy * z11
            )
        else:
            raise ValueError(f"Unsupported interpolation method: '{method}'. Choose 'bilinear' or 'nearest'.")

        return float(elev) if is_scalar else elev

    def get_elevation_geo(
        self,
        lat: Union[float, np.ndarray],
        lon: Union[float, np.ndarray],
        method: str = "bilinear",
    ) -> Union[float, np.ndarray]:
        """
        Query ground surface elevation at geodetic coordinate(s) (lat, lon).
        """
        x, y = self.coordinate_system.geo_to_cartesian(lat, lon)
        return self.get_elevation_cartesian(x, y, method=method)

    @classmethod
    def synthetic_planar(
        cls,
        coordinate_system: LocalCoordinateSystem,
        slope_x: float = 0.0,
        slope_y: float = 0.0,
        base_elevation_m: float = 200.0,
        domain_radius_m: float = 10000.0,
        resolution_m: float = 500.0,
    ) -> "TerrainField":
        """
        Create synthetic analytical planar terrain z(x, y) = base + slope_x * x + slope_y * y
        for deterministic numerical testing without external API dependence.
        """
        xs = np.arange(-domain_radius_m, domain_radius_m + resolution_m, resolution_m)
        ys = np.arange(-domain_radius_m, domain_radius_m + resolution_m, resolution_m)
        X, Y = np.meshgrid(xs, ys)
        Z = base_elevation_m + slope_x * X + slope_y * Y

        provenance = {
            "provider": "SyntheticPlanarDEM",
            "resolution_meters": resolution_m,
            "base_elevation_m": base_elevation_m,
            "slope_x": slope_x,
            "slope_y": slope_y,
            "interpolation": "bilinear",
            "is_synthetic": True,
        }

        return cls(
            coordinate_system=coordinate_system,
            x_coords=xs,
            y_coords=ys,
            elevation_grid=Z,
            provenance=provenance,
        )


class TerrainConnector:
    """
    Connector for retrieving elevation grids from Open-Meteo Elevation API or synthetic generator.

    Parameters
    ----------
    cache : Optional[DataCache], optional
        Data cache manager.
    timeout_seconds : float, default=15.0
        HTTP request timeout.
    """

    ELEVATION_ENDPOINT = "https://api.open-meteo.com/v1/elevation"

    def __init__(
        self,
        cache: Optional[DataCache] = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        self.cache = cache if cache is not None else DataCache()
        self.timeout_seconds = timeout_seconds

    def fetch_elevation_grid(
        self,
        coordinate_system: LocalCoordinateSystem,
        domain_radius_m: float = 5000.0,
        resolution_m: float = 500.0,
        allow_synthetic_fallback: bool = True,
    ) -> TerrainField:
        """
        Fetch gridded elevation over domain from Open-Meteo Elevation API or generate cached grid.

        Parameters
        ----------
        coordinate_system : LocalCoordinateSystem
            Simulation coordinate reference frame.
        domain_radius_m : float, default=5000.0
            Half-width of domain in meters.
        resolution_m : float, default=500.0
            Grid spacing in meters.
        allow_synthetic_fallback : bool, default=True
            Whether to fallback to default planar elevation on API failure.

        Returns
        -------
        TerrainField
            Gridded terrain elevation model.
        """
        xs = np.arange(-domain_radius_m, domain_radius_m + resolution_m, resolution_m)
        ys = np.arange(-domain_radius_m, domain_radius_m + resolution_m, resolution_m)
        nx, ny = len(xs), len(ys)

        # Generate lat/lon coordinates for all grid points
        X, Y = np.meshgrid(xs, ys)
        lats, lons = coordinate_system.cartesian_to_geo(X.ravel(), Y.ravel())

        params = {
            "latitude": [round(float(lat), 4) for lat in lats.ravel()],
            "longitude": [round(float(lon), 4) for lon in lons.ravel()],
        }

        cache_key = self.cache.generate_key("elevation_grid", {
            "origin_lat": coordinate_system.origin_lat,
            "origin_lon": coordinate_system.origin_lon,
            "radius_m": domain_radius_m,
            "res_m": resolution_m,
        })

        raw_json = self.cache.get(cache_key)
        if raw_json is None:
            # Batch query Open-Meteo elevation API if points <= 1000
            if len(lats) <= 1000:
                try:
                    lat_str = ",".join(str(lat) for lat in params["latitude"])
                    lon_str = ",".join(str(lon) for lon in params["longitude"])
                    resp = requests.get(
                        self.ELEVATION_ENDPOINT,
                        params={"latitude": lat_str, "longitude": lon_str},
                        timeout=self.timeout_seconds,
                    )
                    resp.raise_for_status()
                    raw_json = resp.json()
                    self.cache.set(cache_key, raw_json)
                except Exception as exc:
                    if not allow_synthetic_fallback:
                        raise RuntimeError(f"Failed to fetch elevation from {self.ELEVATION_ENDPOINT}: {exc}") from exc
                    raw_json = None
            else:
                raw_json = None

        if raw_json and "elevation" in raw_json:
            elevations = np.array(raw_json["elevation"], dtype=np.float64).reshape((ny, nx))
            provenance = {
                "provider": "Open-Meteo Elevation API (SRTM 90m / Copernicus DEM)",
                "endpoint": self.ELEVATION_ENDPOINT,
                "resolution_meters": resolution_m,
                "domain_radius_m": domain_radius_m,
                "interpolation": "bilinear",
                "vertical_datum": "EGM96",
                "is_synthetic": False,
            }
        else:
            # Fallback to standard 200m base elevation
            elevations = np.full((ny, nx), 200.0, dtype=np.float64)
            provenance = {
                "provider": "DefaultFlatTerrainFallback",
                "resolution_meters": resolution_m,
                "domain_radius_m": domain_radius_m,
                "base_elevation_m": 200.0,
                "interpolation": "bilinear",
                "is_synthetic": True,
            }

        return TerrainField(
            coordinate_system=coordinate_system,
            x_coords=xs,
            y_coords=ys,
            elevation_grid=elevations,
            provenance=provenance,
        )
