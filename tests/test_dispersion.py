"""
Unit tests for atmospheric dispersion coefficients module (Briggs 1973/1974 parameterizations).
"""

import pytest
import numpy as np
from atmosim.physics.stability import StabilityClass
from atmosim.physics.dispersion import (
    EnvironmentType,
    compute_sigma_y,
    compute_sigma_z,
    compute_dispersion_coefficients,
    BRIGGS_MIN_X,
    BRIGGS_MAX_X,
)


class TestDispersionCoefficients:
    """Test dispersion coefficient implementations."""

    @pytest.mark.parametrize("st", list(StabilityClass))
    @pytest.mark.parametrize("env", [EnvironmentType.RURAL, EnvironmentType.URBAN])
    def test_positivity(self, st, env):
        """Verify sigma_y > 0 and sigma_z > 0 for all physical distances x > 0."""
        distances = np.array([10.0, 100.0, 500.0, 1000.0, 5000.0, 10000.0])
        sy, sz = compute_dispersion_coefficients(distances, stability=st, environment=env)
        assert np.all(sy > 0.0)
        assert np.all(sz > 0.0)
        assert np.all(np.isfinite(sy))
        assert np.all(np.isfinite(sz))

    @pytest.mark.parametrize("st", list(StabilityClass))
    @pytest.mark.parametrize("env", [EnvironmentType.RURAL, EnvironmentType.URBAN])
    def test_monotonic_distance_growth(self, st, env):
        """Verify that dispersion coefficients strictly increase with downwind distance."""
        xs = np.linspace(100.0, 10000.0, 50)
        sy, sz = compute_dispersion_coefficients(xs, stability=st, environment=env)
        assert np.all(np.diff(sy) > 0.0)
        assert np.all(np.diff(sz) > 0.0)

    def test_rural_stability_ordering_at_fixed_distance(self):
        """
        Verify that at a fixed distance (e.g. 1000m), unstable classes produce wider
        dispersion than neutral, which in turn produce wider dispersion than stable classes:
        sigma(A) > sigma(B) > sigma(C) > sigma(D) > sigma(E) > sigma(F)
        """
        x = 1000.0
        classes = [
            StabilityClass.A,
            StabilityClass.B,
            StabilityClass.C,
            StabilityClass.D,
            StabilityClass.E,
            StabilityClass.F,
        ]
        sys = [compute_sigma_y(x, st, EnvironmentType.RURAL) for st in classes]
        szs = [compute_sigma_z(x, st, EnvironmentType.RURAL) for st in classes]

        # Check strict monotonic decrease in sigma widths across A -> F
        for i in range(len(classes) - 1):
            assert sys[i] > sys[i + 1], f"sigma_y ordering failed: {classes[i]} ({sys[i]}) <= {classes[i+1]} ({sys[i+1]})"
            assert szs[i] > szs[i + 1], f"sigma_z ordering failed: {classes[i]} ({szs[i]}) <= {classes[i+1]} ({szs[i+1]})"

    def test_exact_analytical_values_rural(self):
        """Verify exact mathematical values of Briggs rural equations at x = 1000 m."""
        x = 1000.0
        # Class A:
        # sigma_y = 0.22 * 1000 / sqrt(1 + 0.1) = 220 / sqrt(1.1) = 209.761769...
        # sigma_z = 0.20 * 1000 = 200.0
        sy_a, sz_a = compute_dispersion_coefficients(x, StabilityClass.A, EnvironmentType.RURAL)
        assert sy_a == pytest.approx(220.0 / np.sqrt(1.1), rel=1e-6)
        assert sz_a == pytest.approx(200.0, rel=1e-6)

        # Class D:
        # sigma_y = 0.08 * 1000 / sqrt(1 + 0.1) = 80 / sqrt(1.1) = 76.277007...
        # sigma_z = 0.06 * 1000 / sqrt(1 + 1.5) = 60 / sqrt(2.5) = 37.947332...
        sy_d, sz_d = compute_dispersion_coefficients(x, StabilityClass.D, EnvironmentType.RURAL)
        assert sy_d == pytest.approx(80.0 / np.sqrt(1.1), rel=1e-6)
        assert sz_d == pytest.approx(60.0 / np.sqrt(2.5), rel=1e-6)

        # Class F:
        # sigma_y = 0.04 * 1000 / sqrt(1 + 0.1) = 40 / sqrt(1.1) = 38.138503...
        # sigma_z = 0.016 * 1000 / (1 + 0.3) = 16 / 1.3 = 12.307692...
        sy_f, sz_f = compute_dispersion_coefficients(x, StabilityClass.F, EnvironmentType.RURAL)
        assert sy_f == pytest.approx(40.0 / np.sqrt(1.1), rel=1e-6)
        assert sz_f == pytest.approx(16.0 / 1.3, rel=1e-6)

    def test_exact_analytical_values_urban(self):
        """Verify exact mathematical values of Briggs urban equations at x = 1000 m."""
        x = 1000.0
        # Urban Class C:
        # sigma_y = 0.22 * 1000 / sqrt(1 + 0.4) = 220 / sqrt(1.4)
        # sigma_z = 0.20 * 1000 = 200.0
        sy_c, sz_c = compute_dispersion_coefficients(x, StabilityClass.C, EnvironmentType.URBAN)
        assert sy_c == pytest.approx(220.0 / np.sqrt(1.4), rel=1e-6)
        assert sz_c == pytest.approx(200.0, rel=1e-6)

    def test_distance_unit_contract_meters(self):
        """
        Audit Regression Test: Verify that distance input x is strictly interpreted in meters (SI).
        At x = 1000 m, sigma_y (Class D Rural) must be ~76.28 m.
        If 1.0 were mistakenly passed (interpreting input as km), sigma_y would be 0.08 m (~1000x smaller).
        """
        x_meters = 1000.0
        sy, sz = compute_dispersion_coefficients(x_meters, StabilityClass.D, EnvironmentType.RURAL)
        assert 70.0 < sy < 80.0
        assert 35.0 < sz < 40.0

        # Contrast with passing x = 1 (1 km mistakenly passed as numeric 1)
        sy_km_error = compute_sigma_y(1.0, StabilityClass.D, EnvironmentType.RURAL)
        assert sy_km_error < 0.1
        # Ratio confirms 1000x physical discrepancy
        assert sy / sy_km_error > 900.0

    def test_scalar_vs_vectorized(self):
        """Verify that vectorized computation matches repeated scalar evaluations."""
        xs = np.array([100.0, 500.0, 1200.0, 4500.0])
        sy_vec, sz_vec = compute_dispersion_coefficients(xs, StabilityClass.B, EnvironmentType.RURAL)

        for i, x in enumerate(xs):
            sy_sc, sz_sc = compute_dispersion_coefficients(float(x), StabilityClass.B, EnvironmentType.RURAL)
            assert isinstance(sy_sc, float)
            assert isinstance(sz_sc, float)
            assert sy_vec[i] == pytest.approx(sy_sc, rel=1e-9)
            assert sz_vec[i] == pytest.approx(sz_sc, rel=1e-9)

    def test_2d_grid_input(self):
        """Verify computation on 2D meshgrids."""
        x_grid = np.tile(np.linspace(100, 1000, 10), (5, 1))
        sy_grid, sz_grid = compute_dispersion_coefficients(x_grid, StabilityClass.C)
        assert sy_grid.shape == (5, 10)
        assert sz_grid.shape == (5, 10)
        assert np.all(sy_grid > 0)

    def test_invalid_distance_inputs(self):
        """Verify rejection of non-positive distances, NaN, and Inf."""
        with pytest.raises(ValueError, match="strictly positive"):
            compute_sigma_y(0.0, StabilityClass.A)

        with pytest.raises(ValueError, match="strictly positive"):
            compute_sigma_y(-100.0, StabilityClass.A)

        with pytest.raises(ValueError, match="strictly positive"):
            compute_sigma_z(np.array([100.0, -50.0, 500.0]), StabilityClass.D)

        with pytest.raises(ValueError, match="NaN or infinite"):
            compute_sigma_y(np.nan, StabilityClass.A)

        with pytest.raises(ValueError, match="NaN or infinite"):
            compute_sigma_z(np.inf, StabilityClass.A)


class TestNearSourceAndEmpiricalRange:
    """Test near-source behavior (x < 100 m) and empirical validity range utilities."""

    def test_is_in_briggs_empirical_range(self):
        """Verify empirical range checker identifies points within and outside [100, 10000] m."""
        from atmosim.physics.dispersion import is_in_briggs_empirical_range

        assert not is_in_briggs_empirical_range(10.0)      # Below 100m
        assert not is_in_briggs_empirical_range(99.9)      # Just below 100m
        assert is_in_briggs_empirical_range(100.0)         # Lower bound
        assert is_in_briggs_empirical_range(1000.0)        # Inside
        assert is_in_briggs_empirical_range(10000.0)       # Upper bound
        assert not is_in_briggs_empirical_range(10001.0)   # Above 10000m

        arr = np.array([50.0, 100.0, 500.0, 10000.0, 15000.0])
        mask = is_in_briggs_empirical_range(arr)
        np.testing.assert_array_equal(mask, [False, True, True, True, False])

    @pytest.mark.parametrize("st", list(StabilityClass))
    @pytest.mark.parametrize("env", [EnvironmentType.RURAL, EnvironmentType.URBAN])
    def test_near_source_positivity_and_monotonicity(self, st, env):
        """
        Verify that for near-source distances below 100m (x in [0.5, 100] m),
        dispersion coefficients remain strictly positive, finite, and monotonically increasing.
        """
        xs = np.linspace(0.5, 100.0, 50)
        sy, sz = compute_dispersion_coefficients(xs, stability=st, environment=env)

        assert np.all(sy > 0.0)
        assert np.all(sz > 0.0)
        assert np.all(np.isfinite(sy))
        assert np.all(np.isfinite(sz))
        assert np.all(np.diff(sy) > 0.0)
        assert np.all(np.diff(sz) > 0.0)

    def test_near_source_asymptotic_taylor_limit(self):
        """
        Mathematical verification test: Verify that as x -> 0+, sigma_y(x) / x algebraically approaches 'a':
        For Class D Rural: a = 0.08. At x = 0.01 m, sigma_y / x = 0.08 / sqrt(1 + 1e-6) = 0.07999996.
        (Note: Tests algebraic limit of equations; does not constitute observational validation below 100m).
        """
        x_small = 0.01
        sy_d = compute_sigma_y(x_small, StabilityClass.D, EnvironmentType.RURAL)
        assert (sy_d / x_small) == pytest.approx(0.08, rel=1e-5)

        # For Class A Rural: a = 0.22
        sy_a = compute_sigma_y(x_small, StabilityClass.A, EnvironmentType.RURAL)
        assert (sy_a / x_small) == pytest.approx(0.22, rel=1e-5)
