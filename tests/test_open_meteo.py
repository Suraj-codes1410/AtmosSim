"""
Unit and verification tests for Open-Meteo meteorology ingestion and circular interpolation.
"""

from datetime import datetime, timezone, timedelta
import json
import math
import numpy as np
import pytest

from atmosim.data.open_meteo import (
    HourlyMeteorologicalRecord,
    MeteorologicalTimeSeries,
    MissingDataPolicy,
    OpenMeteoConnector,
)


@pytest.fixture
def sample_meteo_json():
    with open("tests/fixtures/sample_open_meteo.json", "r", encoding="utf-8") as f:
        return json.load(f)


class TestOpenMeteoParsingAndUnits:
    """Test suite for parsing raw Open-Meteo payloads into structured time series."""

    def test_parse_valid_response(self, sample_meteo_json):
        connector = OpenMeteoConnector()
        ts = connector.parse_response(
            raw_json=sample_meteo_json,
            latitude=28.6139,
            longitude=77.2090,
            start_time=datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc),
        )

        assert len(ts.records) == 48
        assert ts.latitude == 28.6139
        assert ts.longitude == 77.2090
        assert ts.quality_flags["is_complete"] is True
        assert ts.quality_flags["total_hourly_records"] == 48

        # Verify unit contracts
        r0 = ts.records[0]
        assert r0.wind_speed_mps >= 0.0
        assert 0.0 <= r0.wind_direction_deg < 360.0
        assert -50.0 <= r0.temperature_c <= 60.0
        assert 0.0 <= r0.relative_humidity_pct <= 100.0
        assert r0.boundary_layer_height_m > 0.0

    def test_missing_data_fail_fast(self, sample_meteo_json):
        corrupted = json.loads(json.dumps(sample_meteo_json))
        corrupted["hourly"]["wind_speed_10m"][5] = None

        connector = OpenMeteoConnector(missing_data_policy=MissingDataPolicy.FAIL_FAST)
        with pytest.raises(ValueError, match="Missing critical meteorological observation"):
            connector.parse_response(
                raw_json=corrupted,
                latitude=28.6139,
                longitude=77.2090,
                start_time=datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc),
            )

    def test_missing_data_imputation(self, sample_meteo_json):
        corrupted = json.loads(json.dumps(sample_meteo_json))
        corrupted["hourly"]["wind_speed_10m"][5] = None

        connector = OpenMeteoConnector(missing_data_policy=MissingDataPolicy.INTERPOLATE_OR_FORWARD_FILL)
        ts = connector.parse_response(
            raw_json=corrupted,
            latitude=28.6139,
            longitude=77.2090,
            start_time=datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc),
        )

        assert ts.quality_flags["is_complete"] is False
        assert ts.quality_flags["imputed_records"] == 1
        assert ts.provenance["imputed_records_count"] == 1


class TestCircularWindInterpolation:
    """Test suite for trigonometric circular interpolation across 359° -> 0° boundary."""

    def test_circular_interpolation_across_north(self):
        """
        Verify that transitioning from 350° to 10° at midpoint (t=1800s)
        yields exactly 0° (due North), NOT 180° (due South).
        """
        t0 = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 8, 1, 1, 0, tzinfo=timezone.utc)

        r0 = HourlyMeteorologicalRecord(
            timestamp=t0, wind_speed_mps=5.0, wind_direction_deg=350.0,
            temperature_c=25.0, relative_humidity_pct=50.0, boundary_layer_height_m=800.0,
        )
        r1 = HourlyMeteorologicalRecord(
            timestamp=t1, wind_speed_mps=5.0, wind_direction_deg=10.0,
            temperature_c=25.0, relative_humidity_pct=50.0, boundary_layer_height_m=800.0,
        )

        ts = MeteorologicalTimeSeries(
            latitude=28.0, longitude=77.0,
            start_time=t0, end_time=t1,
            records=[r0, r1],
            provenance={},
        )

        # Midpoint: t = 1800 s
        sp, deg, temp, rh, pblh = ts.get_interpolated_state(1800.0)

        assert sp == pytest.approx(5.0, abs=1e-4)
        # Average of 350° (-10°) and +10° is 0° (or 360°)
        assert (deg == pytest.approx(0.0, abs=1e-3) or deg == pytest.approx(360.0, abs=1e-3))
        assert temp == pytest.approx(25.0, abs=1e-4)
        assert rh == pytest.approx(50.0, abs=1e-4)
        assert pblh == pytest.approx(800.0, abs=1e-4)

    def test_circular_interpolation_exact_nodes(self):
        t0 = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 8, 1, 1, 0, tzinfo=timezone.utc)

        r0 = HourlyMeteorologicalRecord(timestamp=t0, wind_speed_mps=4.0, wind_direction_deg=90.0, temperature_c=20.0, relative_humidity_pct=40.0)
        r1 = HourlyMeteorologicalRecord(timestamp=t1, wind_speed_mps=6.0, wind_direction_deg=180.0, temperature_c=24.0, relative_humidity_pct=60.0)

        ts = MeteorologicalTimeSeries(latitude=28.0, longitude=77.0, start_time=t0, end_time=t1, records=[r0, r1], provenance={})

        sp0, deg0, _, _, _ = ts.get_interpolated_state(0.0)
        assert sp0 == pytest.approx(4.0, abs=1e-4)
        assert deg0 == pytest.approx(90.0, abs=1e-3)

        sp1, deg1, _, _, _ = ts.get_interpolated_state(3600.0)
        assert sp1 == pytest.approx(6.0, abs=1e-4)
        assert deg1 == pytest.approx(180.0, abs=1e-3)


class TestWindFieldExport:
    """Test exporting continuous MeteorologicalTimeSeries to Phase 1 WindField."""

    def test_wind_field_velocity_vectors(self):
        t0 = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 8, 1, 1, 0, tzinfo=timezone.utc)

        # Wind from West (270°) -> advects East (+u = +5.0 m/s, v = 0.0)
        r0 = HourlyMeteorologicalRecord(timestamp=t0, wind_speed_mps=5.0, wind_direction_deg=270.0, temperature_c=20.0, relative_humidity_pct=50.0)
        r1 = HourlyMeteorologicalRecord(timestamp=t1, wind_speed_mps=5.0, wind_direction_deg=270.0, temperature_c=20.0, relative_humidity_pct=50.0)

        ts = MeteorologicalTimeSeries(latitude=28.0, longitude=77.0, start_time=t0, end_time=t1, records=[r0, r1], provenance={})
        wf = ts.to_wind_field()

        u, v = wf.get_velocity(0.0, 0.0, 10.0, t=1800.0)
        assert u == pytest.approx(5.0, abs=1e-4)
        assert v == pytest.approx(0.0, abs=1e-4)
