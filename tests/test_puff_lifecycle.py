"""
Unit tests for puff lifecycle management and culling module.
"""

import pytest
import numpy as np
from atmosim.physics.puff_lifecycle import (
    PuffLifecycleConfig,
    PuffLifecycleState,
    PuffCullReason,
    PuffLifecycleStats,
    SpatialBounds,
    evaluate_cull_condition,
)
from atmosim.physics.puff import (
    EmissionSource,
    GaussianPuffConfig,
    GaussianPuffEngine,
    WindField,
)


class TestPuffLifecycleCulling:
    """Test individual and combined puff culling rules."""

    def test_age_culling(self):
        """Puffs exceeding max_age must be culled with MAX_AGE reason."""
        config = PuffLifecycleConfig(max_age=3600.0)  # 1 hour

        # Young puff: age = 1800s -> keep
        should_cull, reason = evaluate_cull_condition(
            age=1800.0, x=100.0, y=100.0, z=10.0, mass=100.0, source_x=0.0, source_y=0.0, config=config
        )
        assert not should_cull
        assert reason == PuffCullReason.NONE

        # Old puff: age = 3601s -> cull
        should_cull, reason = evaluate_cull_condition(
            age=3601.0, x=100.0, y=100.0, z=10.0, mass=100.0, source_x=0.0, source_y=0.0, config=config
        )
        assert should_cull
        assert reason == PuffCullReason.MAX_AGE

    def test_distance_culling(self):
        """Puffs exceeding max_distance from source must be culled with MAX_DISTANCE reason."""
        config = PuffLifecycleConfig(max_distance=20000.0)  # 20 km

        # Within 20km: distance = 15 km -> keep
        should_cull, reason = evaluate_cull_condition(
            age=500.0, x=9000.0, y=12000.0, z=10.0, mass=100.0, source_x=0.0, source_y=0.0, config=config
        )
        assert not should_cull

        # Beyond 20km: distance = 25 km -> cull
        should_cull, reason = evaluate_cull_condition(
            age=500.0, x=15000.0, y=20000.0, z=10.0, mass=100.0, source_x=0.0, source_y=0.0, config=config
        )
        assert should_cull
        assert reason == PuffCullReason.MAX_DISTANCE

    def test_min_mass_culling(self):
        """Puffs depleted below min_mass must be culled with MIN_MASS reason."""
        config = PuffLifecycleConfig(min_mass=1e-4)

        should_cull, reason = evaluate_cull_condition(
            age=100.0, x=100.0, y=100.0, z=10.0, mass=1e-5, source_x=0.0, source_y=0.0, config=config
        )
        assert should_cull
        assert reason == PuffCullReason.MIN_MASS

    def test_spatial_bounds_culling(self):
        """Puffs leaving configured 3D bounding box must be culled with DOMAIN_BOUNDS reason."""
        bounds = SpatialBounds(x_min=-5000, x_max=5000, y_min=-5000, y_max=5000, z_min=0, z_max=2000)
        config = PuffLifecycleConfig(bounds=bounds)

        # Inside box
        should_cull, reason = evaluate_cull_condition(
            age=100.0, x=4000.0, y=-3000.0, z=500.0, mass=100.0, source_x=0.0, source_y=0.0, config=config
        )
        assert not should_cull

        # Outside box (+x breach)
        should_cull, reason = evaluate_cull_condition(
            age=100.0, x=5001.0, y=0.0, z=500.0, mass=100.0, source_x=0.0, source_y=0.0, config=config
        )
        assert should_cull
        assert reason == PuffCullReason.DOMAIN_BOUNDS


class TestMemoryBoundedness:
    """Verify that continuous emissions remain strictly memory-bounded over long simulation horizons."""

    def test_active_puff_count_stabilization(self):
        """
        For continuous emission with release interval dt_rel and max_age T_max,
        the active puff count must stabilize at exactly N_active ~ T_max / dt_rel, preventing memory explosion.
        """
        max_age = 60.0        # Puffs live for 60 seconds
        dt_rel = 10.0         # 1 puff released every 10 seconds -> expect ~6 active puffs
        dt_step = 5.0

        lifecycle_cfg = PuffLifecycleConfig(max_age=max_age)
        engine_cfg = GaussianPuffConfig(
            time_step=dt_step,
            lifecycle_config=lifecycle_cfg,
        )
        engine = GaussianPuffEngine(config=engine_cfg)
        engine.add_source(EmissionSource(source_id="src1", x=0, y=0, z=20, emission_rate=100, release_interval=dt_rel))

        wind = WindField.constant(u=3.0, v=0.0)

        # Run for 300 seconds (5x max_age)
        engine.run(duration=300.0, wind=wind, dt=dt_step)

        # Active puffs should be bounded (around 6-7 puffs)
        assert 5 <= len(engine.active_puffs) <= 7
        assert engine.stats.created_count == 30
        assert engine.stats.culled_count >= 23
        assert engine.stats.active_count == len(engine.active_puffs)

    def test_culling_invariance_for_in_domain_receptors(self):
        """
        Receptors located within the near-field region of interest should produce identical
        concentrations whether distant expired puffs are culled or retained in a wider domain.
        """
        source = EmissionSource(source_id="src", x=0, y=0, z=30, emission_rate=100, release_interval=5.0)
        wind = WindField.constant(u=5.0, v=0.0)

        # Engine 1: Strict age culling at 200s
        cfg1 = GaussianPuffConfig(
            time_step=5.0,
            lifecycle_config=PuffLifecycleConfig(max_age=200.0),
        )
        engine1 = GaussianPuffEngine(config=cfg1)
        engine1.add_source(source)
        engine1.run(duration=150.0, wind=wind)

        # Engine 2: Wide domain (no culling during 150s)
        cfg2 = GaussianPuffConfig(
            time_step=5.0,
            lifecycle_config=PuffLifecycleConfig(max_age=3600.0),
        )
        engine2 = GaussianPuffEngine(config=cfg2)
        engine2.add_source(source)
        engine2.run(duration=150.0, wind=wind)

        # At t=150s, all puffs are <= 150s old, so neither engine has culled in-domain puffs
        rec_x = np.linspace(100.0, 500.0, 10)
        rec_y = np.zeros_like(rec_x)

        c1 = engine1.evaluate(rec_x, rec_y, z_rec=0.0)
        c2 = engine2.evaluate(rec_x, rec_y, z_rec=0.0)

        np.testing.assert_allclose(c1, c2, rtol=1e-12)
