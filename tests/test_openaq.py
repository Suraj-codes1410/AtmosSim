"""Unit tests for OpenAQ ground truth air quality connector."""

import pandas as pd
import pytest
from atmosim.data.openaq import OpenAQConnector, AirQualityRecord
from atmosim.data.cache import DataCache


def test_openaq_connector_initialization(tmp_path):
    cache = DataCache(cache_dir=tmp_path)
    connector = OpenAQConnector(cache=cache)
    assert connector.cache is not None


def test_openaq_spot_check_days(tmp_path):
    cache = DataCache(cache_dir=tmp_path)
    connector = OpenAQConnector(cache=cache)
    spot_data = connector.get_spot_check_ground_truth()
    
    assert isinstance(spot_data, dict)
    expected_dates = ["2022-11-04", "2023-11-03", "2023-11-13", "2024-01-14", "2024-11-18"]
    for d in expected_dates:
        assert d in spot_data
        assert spot_data[d] > 0.0  # Must be positive PM2.5 observation
