"""Unit tests for leakage audits in atmosim.dataset.leakage."""

import pandas as pd
import pytest

from atmosim.dataset.leakage import (
    audit_feature_leakage,
    audit_simulator_state_leakage,
    audit_target_leakage,
    _SIMULATOR_STATE_COLUMNS,
)


def test_audit_feature_leakage_clean():
    df = pd.DataFrame({
        "sample_id": ["s1"],
        "timestamp": [pd.Timestamp("2020-01-01")],
        "wind_speed": [5.0],
        "temperature": [295.0],
        "target_pm25": [12.0],
    })
    report = audit_feature_leakage(df)
    assert report["status"] == "PASS"
    assert len(report["offending_columns"]) == 0


def test_audit_feature_leakage_detected():
    df = pd.DataFrame({
        "sample_id": ["s1"],
        "timestamp": [pd.Timestamp("2020-01-01")],
        "wind_speed": [5.0],
        "future_wind_speed": [6.0],
        "target_lag1": [10.0],
        "target_pm25": [12.0],
    })
    report = audit_feature_leakage(df)
    assert report["status"] == "FAIL"
    assert "future_wind_speed" in report["offending_columns"]
    assert "target_lag1" in report["offending_columns"]
    # target_pm25 itself is the legitimate target, should not be flagged as a feature leakage
    assert "target_pm25" not in report["offending_columns"]


def test_audit_simulator_state_leakage_clean():
    df = pd.DataFrame({
        "sample_id": ["s1"],
        "timestamp": [pd.Timestamp("2020-01-01")],
        "wind_speed": [5.0],
        "target_pm25": [10.0],
    })
    report = audit_simulator_state_leakage(df)
    assert report["status"] == "PASS"
    assert len(report["offending_columns"]) == 0


def test_audit_simulator_state_leakage_detected():
    for forbidden in _SIMULATOR_STATE_COLUMNS[:3]:
        df = pd.DataFrame({
            "sample_id": ["s1"],
            "wind_speed": [5.0],
            forbidden: [1.23],
        })
        report = audit_simulator_state_leakage(df)
        assert report["status"] == "FAIL"
        assert forbidden in report["offending_columns"]


def test_audit_target_leakage():
    df_clean = pd.DataFrame({
        "sample_id": ["s1"],
        "timestamp": [pd.Timestamp("2020-01-01")],
        "region_id": ["R01"],
        "location_id": ["L01"],
        "wind_speed": [5.0],
        "target_pm25": [15.0],
    })
    assert audit_target_leakage(df_clean)["status"] == "PASS"

    # If an extra column containing 'target' or raw simulator 'concentration_pm25' is present among features:
    df_leak1 = df_clean.copy()
    df_leak1["leaked_target_pm25"] = 15.0
    report1 = audit_target_leakage(df_leak1)
    assert report1["status"] == "FAIL"
    assert "leaked_target_pm25" in report1["offending_columns"]

    df_leak2 = df_clean.copy()
    df_leak2["concentration_pm25"] = 14.0
    report2 = audit_target_leakage(df_leak2)
    assert report2["status"] == "FAIL"
    assert "concentration_pm25" in report2["offending_columns"]
