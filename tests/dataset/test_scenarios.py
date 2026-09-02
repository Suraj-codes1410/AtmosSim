"""Tests for dataset scenario generation and related utilities.
"""

import pytest
from atmosim.dataset.scenarios import generate_benchmark_scenarios, get_predefined_regions

def test_scenario_reproducibility():
    scenarios1 = generate_benchmark_scenarios(random_seed=123)
    scenarios2 = generate_benchmark_scenarios(random_seed=123)
    assert len(scenarios1) == len(scenarios2)
    # The first scenario should be identical
    s1 = scenarios1[0]
    s2 = scenarios2[0]
    assert s1.region.region_id == s2.region.region_id
    assert s1.config == s2.config

def test_predefined_regions_nonempty():
    regions = get_predefined_regions()
    assert len(regions) >= 2
    assert all(region.region_id.startswith("R") for region in regions)
