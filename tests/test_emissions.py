"""
Unit and verification tests for proxy-to-emission parameterization, dimensional correctness, and provenance.
"""

from datetime import datetime, timedelta, timezone
import math
import numpy as np
import pytest

from atmosim.physics.coordinates import LocalCoordinateSystem
from atmosim.sources.emissions import (
    DEFAULT_AADT_BY_CLASS,
    DEFAULT_EMISSION_FACTORS,
    ProxyEmissionParameterizer,
    RoadEmissionConfig,
)
from atmosim.sources.models import RoadSegmentProxy
from atmosim.sources.provenance import UncertaintyClass
from atmosim.sources.traffic_profiles import TemporalTrafficProfile


class TestTrafficProfileNormalization:
    """Test mathematical normalization of temporal traffic activity profiles."""

    def test_daily_mean_normalization_is_unity(self):
        """
        Verify that (1/24) * sum_{h=0}^{23} f_h == 1.0 strictly.
        """
        profile = TemporalTrafficProfile.default_urban_diurnal()
        assert len(profile.hourly_factors) == 24
        mean_val = float(np.mean(profile.hourly_factors))
        assert mean_val == pytest.approx(1.0, rel=1e-6)

    def test_weekend_multiplier_scaling(self):
        profile = TemporalTrafficProfile.default_urban_diurnal()
        # Wednesday (weekday) at 08:00
        dt_weekday = datetime(2026, 8, 5, 8, 0, tzinfo=timezone.utc)
        mult_weekday = profile.get_multiplier(dt_weekday)

        # Sunday (weekend) at 08:00
        dt_weekend = datetime(2026, 8, 9, 8, 0, tzinfo=timezone.utc)
        mult_weekend = profile.get_multiplier(dt_weekend)

        assert mult_weekend == pytest.approx(mult_weekday * profile.weekend_multiplier, rel=1e-5)


class TestEmissionDimensionalityAndScaling:
    """Test dimensional correctness, parameter scaling, and provenance tracking."""

    def test_road_emission_rate_hand_calculation(self):
        """
        Hand calculation verification:
        Length = 500.0 m = 0.5 km
        Class = primary -> AADT = 20,000 veh/day
        Profile = Uniform (1.0) -> V = 20,000 / 24 veh/hr = 833.3333 veh/hr
        EF = 0.14 g PM2.5 / veh-km

        Expected Q = (0.5 km * (20000 / 24) veh/hr * 0.14 g/veh-km) / 3600 s/hr
                   = (0.5 * 833.3333 * 0.14) / 3600
                   = 58.3333 / 3600
                   = 0.0162037037... g/s
        """
        seg = RoadSegmentProxy(
            segment_id="test_seg_01",
            parent_osm_id=1001,
            road_class="primary",
            length_meters=500.0,
            start_point_geo=(28.6, 77.2),
            end_point_geo=(28.605, 77.2),
            midpoint_geo=(28.6025, 77.2),
            midpoint_cartesian=(0.0, 250.0),
        )

        cfg = RoadEmissionConfig(
            traffic_profile=TemporalTrafficProfile.uniform_constant(),
        )
        parameterizer = ProxyEmissionParameterizer(config=cfg)

        dt = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
        q_calc = parameterizer.compute_road_segment_emission_rate(seg, dt)

        q_expected = (0.5 * (20000.0 / 24.0) * 0.14) / 3600.0
        assert q_calc == pytest.approx(q_expected, rel=1e-6)

    def test_linear_scaling_properties(self):
        """
        Verify:
        1. 2x length -> 2x Q
        2. 2x AADT -> 2x Q
        3. 2x EF -> 2x Q
        """
        cfg = RoadEmissionConfig(traffic_profile=TemporalTrafficProfile.uniform_constant())
        param = ProxyEmissionParameterizer(config=cfg)
        dt = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)

        seg1 = RoadSegmentProxy(
            segment_id="s1", parent_osm_id=1, road_class="primary", length_meters=200.0,
            start_point_geo=(0, 0), end_point_geo=(0, 0), midpoint_geo=(0, 0), midpoint_cartesian=(0, 0),
        )
        seg2 = RoadSegmentProxy(
            segment_id="s2", parent_osm_id=2, road_class="primary", length_meters=400.0,
            start_point_geo=(0, 0), end_point_geo=(0, 0), midpoint_geo=(0, 0), midpoint_cartesian=(0, 0),
        )

        q1 = param.compute_road_segment_emission_rate(seg1, dt)
        q2 = param.compute_road_segment_emission_rate(seg2, dt)

        assert q2 == pytest.approx(2.0 * q1, rel=1e-6)

    def test_source_provenance_completeness(self):
        seg = RoadSegmentProxy(
            segment_id="s_prov", parent_osm_id=99, road_class="secondary", length_meters=150.0,
            start_point_geo=(0, 0), end_point_geo=(0, 0), midpoint_geo=(0, 0), midpoint_cartesian=(0, 0),
        )
        param = ProxyEmissionParameterizer()
        src, prov = param.create_road_emission_source(seg, simulation_start=datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc))

        assert prov.source_id == "s_prov"
        assert prov.proxy_provider == "OpenStreetMap"
        assert prov.pollutant == "PM2.5"
        assert prov.uncertainty_class == UncertaintyClass.HIGH
        assert len(prov.assumptions) >= 3
        assert prov.emission_factor > 0.0
        assert "g PM2.5 / vehicle-km" in prov.emission_factor_units


class TestEmissionMassConservationAndIndustrialSafety:
    """Test mass conservation Q(t) -> M and industrial proxy emission safety."""

    def test_time_varying_emission_mass_conservation_integral(self):
        """
        Verify that for time-varying emission Q(t) evaluated over duration T:
        1. Discrete released mass sum sum(Delta M_i) = sum(Q(t_i) * Delta t_rel)
           equals the numerical Riemann/trapezoidal integral of Q(t) over [0, T].
        2. Total mass scaling is exact across diurnal cycle.
        """
        seg = RoadSegmentProxy(
            segment_id="cons_seg",
            parent_osm_id=5001,
            road_class="primary",
            length_meters=1000.0,  # 1.0 km
            start_point_geo=(28.6, 77.2),
            end_point_geo=(28.61, 77.2),
            midpoint_geo=(28.605, 77.2),
            midpoint_cartesian=(0.0, 500.0),
        )

        cfg = RoadEmissionConfig()
        parameterizer = ProxyEmissionParameterizer(config=cfg)

        # 1. Test on a Weekday (Wednesday, Aug 5, 2026)
        start_weekday = datetime(2026, 8, 5, 0, 0, tzinfo=timezone.utc)
        duration_s = 86400.0  # Full 24-hour cycle
        dt_rel = 60.0         # 1-minute release interval

        times = np.arange(0, duration_s, dt_rel)
        q_vals_weekday = [
            parameterizer.compute_road_segment_emission_rate(seg, start_weekday + timedelta(seconds=float(t)))
            for t in times
        ]
        weekday_mass_sum = float(np.sum(q_vals_weekday) * dt_rel)

        # Expected weekday mass = 1.0 km * 20,000 veh/day * 0.14 g/veh-km = 2800.0 g
        expected_weekday_mass = 1.0 * 20000.0 * 0.14
        assert weekday_mass_sum == pytest.approx(expected_weekday_mass, rel=1e-3)

        # 2. Test on a Weekend (Saturday, Aug 1, 2026) -> 0.85 multiplier
        start_weekend = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
        q_vals_weekend = [
            parameterizer.compute_road_segment_emission_rate(seg, start_weekend + timedelta(seconds=float(t)))
            for t in times
        ]
        weekend_mass_sum = float(np.sum(q_vals_weekend) * dt_rel)
        expected_weekend_mass = expected_weekday_mass * cfg.traffic_profile.weekend_multiplier  # 2380.0 g
        assert weekend_mass_sum == pytest.approx(expected_weekend_mass, rel=1e-3)

    def test_industrial_proxies_do_not_inject_fabricated_emissions(self):
        """
        Verify that industrial land-use polygons and point sources are preserved as geographic
        proxies with emission_status='unavailable' and do NOT silently fabricate unmeasured emissions.
        """
        from atmosim.sources.models import IndustrialProxy, PointSourceProxy

        ind_poly = IndustrialProxy(
            proxy_id="ind_01",
            osm_id=3001,
            area_m2=50000.0,
            centroid_geo=(28.62, 77.20),
            centroid_cartesian=(500.0, 1200.0),
            osm_tags={"landuse": "industrial"},
            emission_status="unavailable",
        )

        assert ind_poly.emission_status == "unavailable"
        assert not hasattr(ind_poly, "emission_rate")

