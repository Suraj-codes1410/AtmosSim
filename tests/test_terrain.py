"""
Unit and verification tests for TerrainField digital elevation model and spatial interpolation.
"""

import numpy as np
import pytest

from atmosim.data.terrain import TerrainConnector, TerrainField
from atmosim.physics.coordinates import LocalCoordinateSystem


class TestTerrainFieldInterpolation:
    """Test suite for spatial interpolation on synthetic analytical terrain surfaces."""

    def test_synthetic_planar_bilinear_exactness(self):
        """
        Verify that bilinear interpolation on an analytical planar surface
        z(x, y) = 200 + 0.05*x - 0.02*y is exact at all interior query points.
        """
        coord = LocalCoordinateSystem(origin_lat=28.6139, origin_lon=77.2090)
        terrain = TerrainField.synthetic_planar(
            coordinate_system=coord,
            slope_x=0.05,
            slope_y=-0.02,
            base_elevation_m=200.0,
            domain_radius_m=2000.0,
            resolution_m=500.0,
        )

        # Test arbitrary non-grid coordinate (x=350.0, y=-625.0)
        qx, qy = 350.0, -625.0
        z_expected = 200.0 + 0.05 * qx - 0.02 * qy
        z_interp = terrain.get_elevation_cartesian(qx, qy, method="bilinear")

        assert z_interp == pytest.approx(z_expected, rel=1e-6)

    def test_terrain_grid_boundaries_and_extrema(self):
        coord = LocalCoordinateSystem(origin_lat=28.6139, origin_lon=77.2090)
        terrain = TerrainField.synthetic_planar(
            coordinate_system=coord,
            slope_x=0.0,
            slope_y=0.0,
            base_elevation_m=250.0,
            domain_radius_m=1000.0,
            resolution_m=250.0,
        )

        # Exact grid boundary
        z_edge = terrain.get_elevation_cartesian(1000.0, 1000.0)
        assert z_edge == pytest.approx(250.0, abs=1e-5)

        # Outside boundary should raise ValueError
        with pytest.raises(ValueError, match="Coordinates out of terrain coverage"):
            terrain.get_elevation_cartesian(1005.0, 500.0)

    def test_geodetic_elevation_query(self):
        coord = LocalCoordinateSystem(origin_lat=28.6139, origin_lon=77.2090)
        terrain = TerrainField.synthetic_planar(
            coordinate_system=coord,
            base_elevation_m=215.0,
            domain_radius_m=5000.0,
        )

        # At coordinate origin
        z_origin = terrain.get_elevation_geo(28.6139, 77.2090)
        assert z_origin == pytest.approx(215.0, abs=1e-4)


class TestTerrainConnectorFallback:
    """Test connector fallback and offline operation."""

    def test_offline_fallback_generation(self):
        coord = LocalCoordinateSystem(origin_lat=28.6139, origin_lon=77.2090)
        connector = TerrainConnector()
        field = connector.fetch_elevation_grid(
            coordinate_system=coord,
            domain_radius_m=2000.0,
            resolution_m=500.0,
            allow_synthetic_fallback=True,
        )

        assert field.elevation_grid.shape == (9, 9)
        assert np.all(field.elevation_grid > 0.0)
        assert np.all(np.isfinite(field.elevation_grid))
