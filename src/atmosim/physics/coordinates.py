"""
Geographic to Local Cartesian Coordinate Transformation Module for AtmosSim.

Transforms geodetic coordinates (WGS84 latitude/longitude) to a local metric Cartesian
system (x, y in meters) relative to an anchor origin (lat0, lon0) using rigorous conformal
projections (Universal Transverse Mercator or Azimuthal Equidistant via pyproj).

Convention
----------
* Cartesian +x is oriented Eastward (meters).
* Cartesian +y is oriented Northward (meters).
* Cartesian +z is oriented Upward (meters above ground).

References
----------
1. Snyder, J. P. (1987). Map Projections—A Working Manual.
   U.S. Geological Survey Professional Paper 1395, Washington, D.C.
2. Defense Mapping Agency (1989). The Universal Grids: Universal Transverse Mercator (UTM)
   and Universal Polar Stereographic (UPS). DMA Technical Manual 8358.2.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, Union
import math
import numpy as np

try:
    import pyproj
    from pyproj import CRS, Transformer
    PYPROJ_AVAILABLE = True
except ImportError:
    PYPROJ_AVAILABLE = False


def determine_utm_epsg(lat: float, lon: float) -> int:
    """
    Determine the EPSG code for the Universal Transverse Mercator (UTM) zone of a given lat/lon.

    Parameters
    ----------
    lat : float
        Latitude in decimal degrees (-90.0 to 90.0).
    lon : float
        Longitude in decimal degrees (-180.0 to 180.0).

    Returns
    -------
    int
        EPSG code (e.g. 32643 for WGS 84 / UTM zone 43N).
    """
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Latitude must be in range [-90, 90], got {lat}")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"Longitude must be in range [-180, 180], got {lon}")

    zone_number = int(math.floor((lon + 180.0) / 6.0)) + 1
    # Handle Norway / Svalbard special zones if needed, standard formulation for global:
    if lat >= 0:
        return 32600 + zone_number  # Northern Hemisphere
    else:
        return 32700 + zone_number  # Southern Hemisphere


@dataclass(frozen=True)
class LocalCoordinateSystem:
    """
    Local metric Cartesian coordinate reference frame anchored at (origin_lat, origin_lon).

    Parameters
    ----------
    origin_lat : float
        Anchor latitude in decimal degrees.
    origin_lon : float
        Anchor longitude in decimal degrees.
    crs_name : str, optional
        Underlying projected CRS name or EPSG string. If None, auto-selects UTM zone.
    """
    origin_lat: float
    origin_lon: float
    crs_epsg: int = 0

    def __post_init__(self):
        if not (-90.0 <= self.origin_lat <= 90.0):
            raise ValueError(f"Origin latitude out of bounds: {self.origin_lat}")
        if not (-180.0 <= self.origin_lon <= 180.0):
            raise ValueError(f"Origin longitude out of bounds: {self.origin_lon}")

        if not PYPROJ_AVAILABLE:
            raise ImportError(
                "pyproj is required for coordinate projections. Install via 'pip install pyproj'."
            )

        if self.crs_epsg == 0:
            epsg = determine_utm_epsg(self.origin_lat, self.origin_lon)
            object.__setattr__(self, "crs_epsg", epsg)

    @property
    def _transformer_fwd(self) -> "Transformer":
        """Transformer from WGS84 (EPSG:4326) to projected CRS."""
        return Transformer.from_crs("EPSG:4326", f"EPSG:{self.crs_epsg}", always_xy=True)

    @property
    def _transformer_inv(self) -> "Transformer":
        """Transformer from projected CRS to WGS84 (EPSG:4326)."""
        return Transformer.from_crs(f"EPSG:{self.crs_epsg}", "EPSG:4326", always_xy=True)

    @property
    def _origin_projected(self) -> Tuple[float, float]:
        """Projected coordinates (East, North) of the local origin."""
        e0, n0 = self._transformer_fwd.transform(self.origin_lon, self.origin_lat)
        return float(e0), float(n0)

    def geo_to_cartesian(
        self,
        lat: Union[float, np.ndarray],
        lon: Union[float, np.ndarray],
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        """
        Convert geodetic coordinates (lat, lon) to local Cartesian (x, y) in meters.

        Parameters
        ----------
        lat : float or np.ndarray
            Latitude(s) in decimal degrees.
        lon : float or np.ndarray
            Longitude(s) in decimal degrees.

        Returns
        -------
        Tuple[float or np.ndarray, float or np.ndarray]
            (x, y) coordinates in meters relative to local origin (+x=East, +y=North).
        """
        is_scalar = np.isscalar(lat) and np.isscalar(lon)
        lat_arr = np.asanyarray(lat, dtype=np.float64)
        lon_arr = np.asanyarray(lon, dtype=np.float64)

        if np.any((lat_arr < -90.0) | (lat_arr > 90.0)):
            raise ValueError("Latitude out of range [-90, 90]")
        if np.any((lon_arr < -180.0) | (lon_arr > 180.0)):
            raise ValueError("Longitude out of range [-180, 180]")

        e0, n0 = self._origin_projected
        e, n = self._transformer_fwd.transform(lon_arr, lat_arr)

        x = e - e0
        y = n - n0

        return (float(x), float(y)) if is_scalar else (x, y)

    def cartesian_to_geo(
        self,
        x: Union[float, np.ndarray],
        y: Union[float, np.ndarray],
    ) -> Tuple[Union[float, np.ndarray], Union[float, np.ndarray]]:
        """
        Convert local Cartesian coordinates (x, y in meters) back to geodetic (lat, lon).

        Parameters
        ----------
        x : float or np.ndarray
            Local Eastward coordinate in meters.
        y : float or np.ndarray
            Local Northward coordinate in meters.

        Returns
        -------
        Tuple[float or np.ndarray, float or np.ndarray]
            (lat, lon) in decimal degrees.
        """
        is_scalar = np.isscalar(x) and np.isscalar(y)
        x_arr = np.asanyarray(x, dtype=np.float64)
        y_arr = np.asanyarray(y, dtype=np.float64)

        e0, n0 = self._origin_projected
        e = x_arr + e0
        n = y_arr + n0

        lon, lat = self._transformer_inv.transform(e, n)

        return (float(lat), float(lon)) if is_scalar else (lat, lon)
