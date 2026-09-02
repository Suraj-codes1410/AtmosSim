"""
End-to-end integration and verification tests for SimulationInputAssembler and Phase 1 Gaussian Puff Engine coupling.
"""

from datetime import datetime, timezone, timedelta
import json
import numpy as np
import pytest

from atmosim.data.cache import DataCache
from atmosim.data.open_meteo import OpenMeteoConnector
from atmosim.data.overpass import OverpassConnector
from atmosim.data.terrain import TerrainConnector
from atmosim.physics.puff import GaussianPuffConfig
from atmosim.simulation.input_assembler import SimulationInputAssembler, SimulationInput


@pytest.fixture
def assembler_with_fixtures(tmp_path):
    cache = DataCache(cache_dir=tmp_path / "cache")

    # Load fixtures and prime cache
    with open("tests/fixtures/sample_open_meteo.json", "r") as f:
        meteo_data = json.load(f)
    with open("tests/fixtures/sample_overpass_roads.json", "r") as f:
        osm_data = json.load(f)
    with open("tests/fixtures/sample_elevation.json", "r") as f:
        elev_data = json.load(f)

    meteo_conn = OpenMeteoConnector(cache=cache)
    terrain_conn = TerrainConnector(cache=cache)
    overpass_conn = OverpassConnector(cache=cache)

    # Mock fetch methods to return parsed fixture representations
    assembler = SimulationInputAssembler(
        cache=cache,
        meteo_connector=meteo_conn,
        terrain_connector=terrain_conn,
        overpass_connector=overpass_conn,
    )

    # Monkeypatch connector fetch methods to avoid live network access
    meteo_conn.fetch_meteorology = lambda latitude, longitude, start_time, end_time, **kwargs: meteo_conn.parse_response(
        raw_json=meteo_data, latitude=latitude, longitude=longitude, start_time=start_time, end_time=end_time,
    )
    overpass_conn.fetch_features = lambda min_lat, min_lon, max_lat, max_lon, **kwargs: overpass_conn.parse_response(
        raw_json=osm_data
    )

    return assembler


class TestSimulationInputAssembly:
    """Test suite for complete simulation input assembly."""

    def test_end_to_end_assembly_and_manifest(self, assembler_with_fixtures):
        start_t = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
        end_t = datetime(2026, 8, 1, 6, 0, tzinfo=timezone.utc)

        sim_input = assembler_with_fixtures.build(
            latitude=28.6139,
            longitude=77.2090,
            start_time=start_t,
            end_time=end_t,
            domain_radius_m=2000.0,
            terrain_resolution_m=500.0,
        )

        assert isinstance(sim_input, SimulationInput)
        assert sim_input.duration_seconds == 21600.0
        assert len(sim_input.sources) > 0
        assert len(sim_input.source_provenance) == len(sim_input.sources)
        assert sim_input.input_hash is not None
        assert len(sim_input.input_hash) == 64  # SHA-256 hex string

        # Verify manifest
        manifest = sim_input.input_manifest
        assert manifest["version"] == "AtmosSim_Phase2_v1.0"
        assert manifest["domain"]["latitude"] == 28.6139
        assert manifest["domain"]["longitude"] == 77.2090
        assert manifest["sources_summary"]["total_active_emission_sources"] == len(sim_input.sources)

    def test_spatial_coordinate_alignment(self, assembler_with_fixtures):
        start_t = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
        end_t = datetime(2026, 8, 1, 1, 0, tzinfo=timezone.utc)

        sim_input = assembler_with_fixtures.build(
            latitude=28.6139,
            longitude=77.2090,
            start_time=start_t,
            end_time=end_t,
            domain_radius_m=3000.0,
        )

        # Coordinate origin check: (lat0, lon0) -> (0, 0)
        x0, y0 = sim_input.coordinate_system.geo_to_cartesian(28.6139, 77.2090)
        assert x0 == pytest.approx(0.0, abs=1e-4)
        assert y0 == pytest.approx(0.0, abs=1e-4)

        # Verify all source locations lie within domain bounds
        r = sim_input.domain_radius_m
        for src in sim_input.sources:
            assert -r <= src.x <= r
            assert -r <= src.y <= r
            assert src.z >= 0.0


class TestPhysicsDataCouplingWithPhase1PuffEngine:
    """Test coupling assembled simulation inputs with the frozen Phase 1 Gaussian Puff Engine."""

    def test_run_puff_engine_with_assembled_inputs(self, assembler_with_fixtures):
        start_t = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
        end_t = datetime(2026, 8, 1, 1, 0, tzinfo=timezone.utc)

        sim_input = assembler_with_fixtures.build(
            latitude=28.6139,
            longitude=77.2090,
            start_time=start_t,
            end_time=end_t,
            domain_radius_m=2000.0,
        )

        # Initialize Phase 1 engine from assembled inputs
        engine = sim_input.to_puff_engine(config=GaussianPuffConfig(time_step=2.0))
        wind_field = sim_input.get_wind_field()

        # Run simulation for 60 seconds
        engine.run(duration=60.0, wind=wind_field, dt=2.0)

        assert len(engine.active_puffs) > 0
        for puff in engine.active_puffs:
            assert np.isfinite(puff.x)
            assert np.isfinite(puff.y)
            assert puff.mass > 0.0
            assert puff.sigma_x > 0.0
            assert puff.sigma_y > 0.0
            assert puff.sigma_z > 0.0

        # Evaluate concentration at downwind receptors
        rx = np.linspace(-500, 500, 20)
        ry = np.linspace(-500, 500, 20)
        RX, RY = np.meshgrid(rx, ry)
        RZ = np.zeros_like(RX)

        conc = engine.evaluate(RX.ravel(), RY.ravel(), RZ.ravel())

        assert conc.shape == RX.ravel().shape
        assert np.all(np.isfinite(conc))
        assert np.all(conc >= 0.0)
        assert np.max(conc) > 0.0

    def test_end_to_end_puff_mass_conservation_from_simulation_input(self, assembler_with_fixtures):
        """
        Verify end-to-end mass conservation:
        sum of all active puff masses equals the sum of discrete released masses Q(t_k) * Delta t_rel.
        """
        start_t = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
        end_t = datetime(2026, 8, 1, 1, 0, tzinfo=timezone.utc)

        sim_input = assembler_with_fixtures.build(
            latitude=28.6139,
            longitude=77.2090,
            start_time=start_t,
            end_time=end_t,
            domain_radius_m=3000.0,
        )

        engine = sim_input.to_puff_engine(config=GaussianPuffConfig(time_step=5.0))
        wind = sim_input.get_wind_field()

        # Run 50 seconds (10 steps) with release interval = 10s -> 5 releases per source
        duration = 50.0
        engine.run(duration=duration, wind=wind, dt=5.0)

        # Expected mass per source = sum_{t in [0, 10, 20, 30, 40]} Q(t) * 10s
        expected_total_mass = 0.0
        for src in sim_input.sources:
            for t_rel in [0.0, 10.0, 20.0, 30.0, 40.0]:
                expected_total_mass += src.get_emission_rate(t_rel) * src.release_interval

        actual_active_mass = sum(p.mass for p in engine.active_puffs)
        assert actual_active_mass == pytest.approx(expected_total_mass, rel=1e-6)

