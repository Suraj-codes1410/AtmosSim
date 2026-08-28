"""
Unit tests for puff dispersion growth across Pasquill stability classes and extreme regimes.
"""

import pytest
import numpy as np
from atmosim.physics.stability import StabilityClass
from atmosim.physics.dispersion import EnvironmentType
from atmosim.physics.puff import (
    EmissionSource,
    GaussianPuffConfig,
    GaussianPuffEngine,
    WindField,
)


class TestPuffStabilityInteraction:
    """Test puff dispersion growth across stability classes A through F."""

    @pytest.mark.parametrize("st", list(StabilityClass))
    def test_all_stability_classes_growth(self, st):
        """Verify that puffs stably grow in all 6 stability classes without NaN/Inf."""
        cfg = GaussianPuffConfig(stability=st, time_step=5.0)
        engine = GaussianPuffEngine(config=cfg)
        engine.add_source(EmissionSource(source_id="src", x=0, y=0, z=20, emission_rate=100.0, release_interval=20.0))
        wind = WindField.constant(u=4.0, v=0.0)

        engine.run(duration=100.0, wind=wind)

        assert len(engine.active_puffs) > 0
        for p in engine.active_puffs:
            assert p.sigma_x > 1.0
            assert p.sigma_y > 1.0
            assert p.sigma_z > 1.0
            assert np.isfinite(p.sigma_x)
            assert np.isfinite(p.sigma_y)
            assert np.isfinite(p.sigma_z)

    def test_stability_ordering_puff_dispersion(self):
        """
        At identical puff age / travel distance, unstable classes must produce wider
        puffs than neutral, which in turn produce wider puffs than stable classes:
        sigma_A > sigma_D > sigma_F.
        """
        wind = WindField.constant(u=4.0, v=0.0)
        classes = [StabilityClass.A, StabilityClass.D, StabilityClass.F]
        puffs_by_class = {}

        for st in classes:
            cfg = GaussianPuffConfig(stability=st, time_step=5.0)
            eng = GaussianPuffEngine(config=cfg)
            eng.add_source(EmissionSource(source_id="src", x=0, y=0, z=20, emission_rate=100.0, release_interval=100.0))
            eng.run(duration=60.0, wind=wind)
            puffs_by_class[st] = eng.active_puffs[0]

        p_a = puffs_by_class[StabilityClass.A]
        p_d = puffs_by_class[StabilityClass.D]
        p_f = puffs_by_class[StabilityClass.F]

        # Horizontal dispersion ordering
        assert p_a.sigma_y > p_d.sigma_y > p_f.sigma_y
        assert p_a.sigma_x > p_d.sigma_x > p_f.sigma_x

        # Vertical dispersion ordering
        assert p_a.sigma_z > p_d.sigma_z > p_f.sigma_z

    def test_urban_vs_rural_puff_dispersion(self):
        """Urban roughness produces wider horizontal dispersion than rural terrain."""
        wind = WindField.constant(u=4.0, v=0.0)

        # Rural
        eng_rural = GaussianPuffEngine(config=GaussianPuffConfig(environment=EnvironmentType.RURAL, stability=StabilityClass.D))
        eng_rural.add_source(EmissionSource(source_id="src", x=0, y=0, z=20, emission_rate=100, release_interval=100))
        eng_rural.run(duration=60.0, wind=wind)
        p_rural = eng_rural.active_puffs[0]

        # Urban
        eng_urban = GaussianPuffEngine(config=GaussianPuffConfig(environment=EnvironmentType.URBAN, stability=StabilityClass.D))
        eng_urban.add_source(EmissionSource(source_id="src", x=0, y=0, z=20, emission_rate=100, release_interval=100))
        eng_urban.run(duration=60.0, wind=wind)
        p_urban = eng_urban.active_puffs[0]

        assert p_urban.sigma_y > p_rural.sigma_y
        assert p_urban.sigma_z > p_rural.sigma_z
