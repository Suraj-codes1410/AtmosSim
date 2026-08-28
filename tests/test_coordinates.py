"""
Unit tests for geographic to local Cartesian coordinate transformation module.
"""

import pytest
import numpy as np
from atmosim.physics.coordinates import (
    determine_utm_epsg,
    LocalCoordinateSystem,
)


class TestCoordinateTransformations:
    """Test UTM zone selection, projection, and geodetic round-tripping."""

    @pytest.mark.parametrize(
        "lat, lon, expected_epsg",
        [
            (28.6139, 77.2090, 32643),  # New Delhi, India -> UTM Zone 43N
            (51.5074, -0.1278, 32630),  # London, UK -> UTM Zone 30N
            (40.7128, -74.0060, 32618), # New York, USA -> UTM Zone 18N
            (35.6762, 139.6503, 32654), # Tokyo, Japan -> UTM Zone 54N
            (-33.8688, 151.2093, 32756),# Sydney, Australia -> UTM Zone 56S
        ],
    )
    def test_utm_zone_determination(self, lat, lon, expected_epsg):
        """Verify automatic UTM zone EPSG code determination across globe."""
        epsg = determine_utm_epsg(lat, lon)
        assert epsg == expected_epsg

    def test_origin_maps_to_zero(self):
        """The reference origin (lat0, lon0) must map exactly to (0.0, 0.0) meters."""
        lat0, lon0 = 28.6139, 77.2090
        coord_sys = LocalCoordinateSystem(origin_lat=lat0, origin_lon=lon0)

        x0, y0 = coord_sys.geo_to_cartesian(lat0, lon0)
        assert x0 == pytest.approx(0.0, abs=1e-5)
        assert y0 == pytest.approx(0.0, abs=1e-5)

    def test_round_trip_accuracy(self):
        """
        Verify sub-millimeter round-trip numerical consistency (< 1e-4 m) for forward and reverse round-trip:
        (lat, lon) -> (x, y) -> (lat_rt, lon_rt) -> (x_rt, y_rt)
        """
        lat0, lon0 = 28.6139, 77.2090
        coord_sys = LocalCoordinateSystem(origin_lat=lat0, origin_lon=lon0)

        test_points = [
            (28.6139, 77.2090),  # Origin
            (28.6500, 77.2500),  # ~5 km Northeast
            (28.5500, 77.1500),  # ~8 km Southwest
            (28.7000, 77.2090),  # ~9.5 km North
            (28.6139, 77.3000),  # ~8.9 km East
        ]

        for lat, lon in test_points:
            x, y = coord_sys.geo_to_cartesian(lat, lon)
            lat_rt, lon_rt = coord_sys.cartesian_to_geo(x, y)

            assert lat_rt == pytest.approx(lat, abs=1e-7)
            assert lon_rt == pytest.approx(lon, abs=1e-7)

            x_rt, y_rt = coord_sys.geo_to_cartesian(lat_rt, lon_rt)
            assert x_rt == pytest.approx(x, abs=1e-4)  # sub-millimeter
            assert y_rt == pytest.approx(y, abs=1e-4)

    def test_cardinal_directions(self):
        """Verify that moving North increases y, and moving East increases x."""
        lat0, lon0 = 28.6139, 77.2090
        coord_sys = LocalCoordinateSystem(origin_lat=lat0, origin_lon=lon0)

        # North offset
        _, y_north = coord_sys.geo_to_cartesian(lat0 + 0.05, lon0)
        assert y_north > 5000.0  # ~5.5 km North

        # South offset
        _, y_south = coord_sys.geo_to_cartesian(lat0 - 0.05, lon0)
        assert y_south < -5000.0

        # East offset
        x_east, _ = coord_sys.geo_to_cartesian(lat0, lon0 + 0.05)
        assert x_east > 4000.0  # ~4.8 km East

        # West offset
        x_west, _ = coord_sys.geo_to_cartesian(lat0, lon0 - 0.05)
        assert x_west < -4000.0

    def test_vectorized_arrays(self):
        """Verify conversion with 1D NumPy arrays."""
        lat0, lon0 = 28.6139, 77.2090
        coord_sys = LocalCoordinateSystem(origin_lat=lat0, origin_lon=lon0)

        lats = np.array([28.60, 28.61, 28.62, 28.63])
        lons = np.array([77.20, 77.21, 77.22, 77.23])

        xs, ys = coord_sys.geo_to_cartesian(lats, lons)
        assert isinstance(xs, np.ndarray)
        assert isinstance(ys, np.ndarray)
        assert xs.shape == (4,)
        assert ys.shape == (4,)

        lats_rt, lons_rt = coord_sys.cartesian_to_geo(xs, ys)
        np.testing.assert_allclose(lats_rt, lats, atol=1e-7)
        np.testing.assert_allclose(lons_rt, lons, atol=1e-7)

    def test_out_of_bounds_rejection(self):
        """Verify rejection of invalid latitude/longitude degrees."""
        with pytest.raises(ValueError, match="Latitude"):
            determine_utm_epsg(95.0, 77.0)

        with pytest.raises(ValueError, match="Longitude"):
            determine_utm_epsg(28.0, 195.0)

        with pytest.raises(ValueError, match="latitude out of bounds"):
            LocalCoordinateSystem(origin_lat=-100.0, origin_lon=0.0)
