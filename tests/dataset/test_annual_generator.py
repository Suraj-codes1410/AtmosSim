"""
Unit tests for AnnualDatasetGenerator and structured regime quality flags.
"""

from datetime import datetime, timezone
import pytest
import pandas as pd

from atmosim.dataset.annual_generator import (
    AnnualDatasetGenerator,
    RegimeMetadata,
    classify_regime_and_quality,
)


def test_classify_regime_and_quality_stubble():
    dt_stubble = datetime(2023, 11, 5, 12, 0, tzinfo=timezone.utc)
    meta = classify_regime_and_quality(dt_stubble)
    assert meta.regime == "stubble_burning"
    assert meta.confidence_level == "medium"
    assert meta.known_bias_direction == "negative"
    assert "Underpredicts" in meta.systematic_bias_note


def test_classify_regime_and_quality_winter_fog():
    dt_fog = datetime(2023, 1, 15, 6, 0, tzinfo=timezone.utc)
    meta = classify_regime_and_quality(dt_fog)
    assert meta.regime == "winter_fog_inversion"
    assert meta.confidence_level == "medium"
    assert meta.known_bias_direction == "negative"


def test_classify_regime_and_quality_monsoon():
    dt_monsoon = datetime(2023, 7, 20, 14, 0, tzinfo=timezone.utc)
    meta = classify_regime_and_quality(dt_monsoon)
    assert meta.regime == "south_asian_monsoon"
    assert meta.confidence_level == "medium"
    assert meta.known_bias_direction == "positive"


def test_classify_regime_and_quality_moderate():
    dt_spring = datetime(2023, 3, 20, 10, 0, tzinfo=timezone.utc)
    meta = classify_regime_and_quality(dt_spring)
    assert meta.regime == "dry_moderate_transition"
    assert meta.confidence_level == "high"
    assert meta.known_bias_direction == "unbiased"
