"""
Unit tests for RegionalBackgroundConnector and RegionalBackgroundTimeSeries.
"""

from datetime import datetime, timezone
import json
import pytest

from atmosim.data.regional_background import (
    HourlyRegionalRecord,
    RegionalBackgroundConnector,
    RegionalBackgroundSource,
    RegionalBackgroundTimeSeries,
    IGP_SEASONAL_BACKGROUND_PM25,
)
from atmosim.data.cache import DataCache


def test_regional_timeseries_interpolation():
    t0 = datetime(2023, 11, 3, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2023, 11, 3, 1, 0, tzinfo=timezone.utc)
    t2 = datetime(2023, 11, 3, 2, 0, tzinfo=timezone.utc)

    records = [
        HourlyRegionalRecord(timestamp=t0, pm2_5_ug_m3=100.0, pm10_ug_m3=180.0),
        HourlyRegionalRecord(timestamp=t1, pm2_5_ug_m3=150.0, pm10_ug_m3=250.0),
        HourlyRegionalRecord(timestamp=t2, pm2_5_ug_m3=200.0, pm10_ug_m3=300.0),
    ]

    ts = RegionalBackgroundTimeSeries(
        latitude=28.6139,
        longitude=77.2090,
        start_time=t0,
        end_time=t2,
        records=records,
        provenance={"provider": "test"},
    )

    # Test bounds & interpolation
    assert ts.get_interpolated_pm25(0.0) == 100.0
    assert ts.get_interpolated_pm25(3600.0) == 150.0
    assert ts.get_interpolated_pm25(7200.0) == 200.0
    assert pytest.approx(ts.get_interpolated_pm25(1800.0), 0.1) == 125.0
    assert pytest.approx(ts.get_mean_pm25(), 0.1) == 150.0


def test_regional_seasonal_fallback():
    connector = RegionalBackgroundConnector(force_fallback=True)
    t0 = datetime(2023, 11, 3, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2023, 11, 3, 23, 0, tzinfo=timezone.utc)

    ts = connector.query(latitude=28.6139, longitude=77.2090, start_time=t0, end_time=t1)
    assert ts.quality_flags["is_fallback"] is True
    assert ts.provenance["source_type"] == RegionalBackgroundSource.SEASONAL_BASELINE.value
    assert len(ts.records) == 24
    # Check November baseline magnitude
    assert ts.records[0].pm2_5_ug_m3 > 100.0


def test_regional_cams_parsing(tmp_path):
    cache = DataCache(cache_dir=tmp_path)
    connector = RegionalBackgroundConnector(cache=cache)
    t0 = datetime(2023, 11, 3, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2023, 11, 3, 2, 0, tzinfo=timezone.utc)

    mock_payload = {
        "hourly": {
            "time": ["2023-11-03T00:00", "2023-11-03T01:00", "2023-11-03T02:00"],
            "pm2_5": [95.2, 110.5, 105.0],
            "pm10": [180.0, 210.0, 200.0],
        }
    }

    params = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "start_date": "2023-11-03",
        "end_date": "2023-11-03",
        "hourly": "pm2_5,pm10",
        "timezone": "UTC",
    }
    cache_key = cache.generate_key("cams_air_quality", params)
    cache.set(cache_key, mock_payload)

    ts = connector.query(latitude=28.6139, longitude=77.2090, start_time=t0, end_time=t1)
    assert len(ts.records) == 3
    assert ts.records[0].pm2_5_ug_m3 == 95.2
    assert ts.records[1].pm2_5_ug_m3 == 110.5
    assert pytest.approx(ts.get_mean_pm25(), 0.1) == 103.57
    assert ts.quality_flags["is_fallback"] is False
