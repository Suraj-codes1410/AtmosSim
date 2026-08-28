"""
Comprehensive analytical and physical verification unit tests for Gaussian Plume model.

Includes analytical sanity checks, scaling laws, symmetry invariants, mass flux conservation
convergence across multi-scale domains, and independently derived analytical reference test cases.
"""

import pytest
import numpy as np
from scipy.integrate import dblquad

from atmosim.physics.stability import StabilityClass
from atmosim.physics.dispersion import EnvironmentType, compute_dispersion_coefficients
from atmosim.physics.plume import (
    gaussian_plume_concentration,
    GaussianPlumeModel,
)


class TestGaussianPlumeBasics:
    """Core physics and invariant tests for the Gaussian Plume model."""

    # Test 1 — Zero / invalid wind speed rejection
    def test_invalid_wind_speed_rejection(self):
        """The solver must reject u <= 0 with an explicit validation error."""
        with pytest.raises(ValueError, match="strictly positive"):
            gaussian_plume_concentration(
                y=0.0, z=0.0, Q=100.0, wind_speed=0.0, effective_height=30.0, sigma_y=50.0, sigma_z=20.0
            )

        with pytest.raises(ValueError, match="strictly positive"):
            gaussian_plume_concentration(
                y=0.0, z=0.0, Q=100.0, wind_speed=-3.5, effective_height=30.0, sigma_y=50.0, sigma_z=20.0
            )

        with pytest.raises(ValueError, match="strictly positive"):
            GaussianPlumeModel(Q=100.0, wind_speed=0.0, effective_height=30.0, stability=StabilityClass.D)

    # Test 2 — Non-negative concentration
    def test_non_negative_concentration(self):
        """For valid physical inputs, C >= 0 must strictly hold."""
        ys = np.linspace(-1000, 1000, 50)
        zs = np.linspace(0, 500, 50)
        y_grid, z_grid = np.meshgrid(ys, zs)
        c = gaussian_plume_concentration(
            y=y_grid,
            z=z_grid,
            Q=150.0,
            wind_speed=4.5,
            effective_height=40.0,
            sigma_y=80.0,
            sigma_z=35.0,
        )
        assert np.all(c >= 0.0)
        assert np.all(np.isfinite(c))

    # Test 3 — Centerline maximum
    def test_centerline_maximum(self):
        """At fixed x and z, concentration must be maximal at the crosswind centerline y=0."""
        ys = np.linspace(-500, 500, 101)  # contains y=0 at index 50
        c = gaussian_plume_concentration(
            y=ys,
            z=0.0,
            Q=100.0,
            wind_speed=3.0,
            effective_height=25.0,
            sigma_y=60.0,
            sigma_z=30.0,
        )
        max_idx = np.argmax(c)
        assert ys[max_idx] == pytest.approx(0.0, abs=1e-9)
        assert c[max_idx] >= np.max(c)

    # Test 4 & 12 — Crosswind symmetry
    def test_crosswind_symmetry(self):
        """For equivalent points (x, +y, z) and (x, -y, z), concentration must match exactly."""
        ys_pos = np.array([5.0, 25.0, 100.0, 350.0, 750.0])
        ys_neg = -ys_pos

        c_pos = gaussian_plume_concentration(
            y=ys_pos,
            z=10.0,
            Q=200.0,
            wind_speed=5.0,
            effective_height=50.0,
            sigma_y=120.0,
            sigma_z=45.0,
        )
        c_neg = gaussian_plume_concentration(
            y=ys_neg,
            z=10.0,
            Q=200.0,
            wind_speed=5.0,
            effective_height=50.0,
            sigma_y=120.0,
            sigma_z=45.0,
        )
        np.testing.assert_allclose(c_pos, c_neg, rtol=1e-12, atol=1e-15)

    # Test 5 — Crosswind decay
    def test_crosswind_monotonic_decay(self):
        """Concentration must monotonically decay as |y| increases away from the centerline."""
        ys = np.linspace(0.0, 800.0, 100)
        c = gaussian_plume_concentration(
            y=ys,
            z=0.0,
            Q=100.0,
            wind_speed=4.0,
            effective_height=30.0,
            sigma_y=100.0,
            sigma_z=40.0,
        )
        assert np.all(np.diff(c) <= 0.0)

    # Test 6 — Downwind behavior under controlled dispersion
    def test_downwind_behavior_ground_source(self):
        """For a ground-level source (H=0, z=0), ground centerline concentration monotonically decreases with x."""
        model = GaussianPlumeModel(
            Q=100.0,
            wind_speed=4.0,
            effective_height=0.0,  # Ground level release
            stability=StabilityClass.D,
        )
        xs = np.linspace(100.0, 5000.0, 100)
        c = model.evaluate(x=xs, y=0.0, z=0.0)
        # For H=0, C_centerline = Q / (pi * u * sy(x) * sz(x)). Since sy and sz both increase with x, C strictly decreases.
        assert np.all(np.diff(c) < 0.0)

    def test_downwind_elevated_source_peaking_behavior(self):
        """
        For an elevated source (H > 0), ground-level centerline concentration C(x, y=0, z=0)
        starts near zero close to the stack, reaches a maximum at downwind distance x_max,
        and then monotonically decreases in the far field as vertical diffusion expands.
        """
        model = GaussianPlumeModel(
            Q=100.0,
            wind_speed=4.0,
            effective_height=50.0,
            stability=StabilityClass.C,
        )
        xs = np.linspace(100.0, 10000.0, 200)
        c = model.evaluate(x=xs, y=0.0, z=0.0)
        max_idx = np.argmax(c)
        # Maximum ground impact must occur downwind (not at the stack x=100m)
        assert xs[max_idx] > 300.0
        # Beyond the peak, far-field ground concentration decays monotonically
        far_field_c = c[max_idx:]
        assert np.all(np.diff(far_field_c) < 0.0)

    # Test 7 — Reflection term contribution (method of images)
    def test_ground_reflection_term(self):
        """
        At ground level (z=0), the reflected plume term exp(-(0+H)^2/(2*sz^2))
        is identical to the direct term exp(-(0-H)^2/(2*sz^2)), exactly doubling ground concentration.
        """
        Q = 100.0
        u = 4.0
        H = 35.0
        sy = 75.0
        sz = 30.0

        c_with_refl = gaussian_plume_concentration(
            y=50.0, z=0.0, Q=Q, wind_speed=u, effective_height=H, sigma_y=sy, sigma_z=sz, include_ground_reflection=True
        )
        c_no_refl = gaussian_plume_concentration(
            y=50.0, z=0.0, Q=Q, wind_speed=u, effective_height=H, sigma_y=sy, sigma_z=sz, include_ground_reflection=False
        )

        assert c_with_refl == pytest.approx(2.0 * c_no_refl, rel=1e-12)

    # Test 8 — Emission linearity scaling
    def test_emission_rate_linearity(self):
        """Steady-state concentration must scale linearly with emission rate Q: C(2Q) = 2 * C(Q)."""
        Q1 = 75.0
        Q2 = 150.0  # 2 * Q1

        model1 = GaussianPlumeModel(Q=Q1, wind_speed=3.5, effective_height=25.0, stability=StabilityClass.C)
        model2 = GaussianPlumeModel(Q=Q2, wind_speed=3.5, effective_height=25.0, stability=StabilityClass.C)

        x_pts = np.array([200.0, 800.0, 2500.0])
        y_pts = np.array([0.0, 50.0, 150.0])

        c1 = model1.evaluate(x=x_pts, y=y_pts, z=0.0)
        c2 = model2.evaluate(x=x_pts, y=y_pts, z=0.0)

        np.testing.assert_allclose(c2, 2.0 * c1, rtol=1e-12)

    # Test 9 — Wind-speed inverse scaling
    def test_wind_speed_inverse_scaling(self):
        """Under fixed dispersion coefficients, concentration scales inversely with wind speed: C(u2) = (u1/u2) * C(u1)."""
        u1 = 2.0
        u2 = 6.0
        sy = 80.0
        sz = 30.0

        c1 = gaussian_plume_concentration(y=20.0, z=5.0, Q=100.0, wind_speed=u1, effective_height=30.0, sigma_y=sy, sigma_z=sz)
        c2 = gaussian_plume_concentration(y=20.0, z=5.0, Q=100.0, wind_speed=u2, effective_height=30.0, sigma_y=sy, sigma_z=sz)

        assert c2 == pytest.approx((u1 / u2) * c1, rel=1e-12)

    # Test 10 — Grid evaluation and vectorization
    def test_grid_mesh_evaluation(self):
        """Passing 2D NumPy meshgrid evaluates correctly with matching 2D output shape."""
        model = GaussianPlumeModel(Q=100.0, wind_speed=4.0, effective_height=30.0, stability=StabilityClass.D)
        xs = np.linspace(100.0, 2000.0, 40)
        ys = np.linspace(-300.0, 300.0, 30)
        x_grid, y_grid = np.meshgrid(xs, ys)

        c = model.evaluate(x=x_grid, y=y_grid, z=0.0)

        assert c.shape == (30, 40)
        assert np.all(np.isfinite(c))
        assert np.all(c >= 0.0)

    # Test 11 — Scalar evaluation
    def test_scalar_evaluation(self):
        """Scalar inputs produce scalar float results."""
        model = GaussianPlumeModel(Q=100.0, wind_speed=4.0, effective_height=30.0, stability=StabilityClass.D)
        c = model.evaluate(x=1000.0, y=0.0, z=0.0)
        assert isinstance(c, float)
        assert c > 0.0

    # Input validation tests
    def test_input_validation(self):
        """Verify explicit validation errors for invalid physical inputs."""
        # Negative Q
        with pytest.raises(ValueError, match="Emission rate Q must be a non-negative"):
            gaussian_plume_concentration(y=0.0, z=0.0, Q=-10.0, wind_speed=4.0, effective_height=30.0, sigma_y=50.0, sigma_z=20.0)

        # Negative H
        with pytest.raises(ValueError, match="Effective source height H must be non-negative"):
            gaussian_plume_concentration(y=0.0, z=0.0, Q=10.0, wind_speed=4.0, effective_height=-30.0, sigma_y=50.0, sigma_z=20.0)

        # Negative z
        with pytest.raises(ValueError, match="Receptor height z must be non-negative"):
            gaussian_plume_concentration(y=0.0, z=-5.0, Q=10.0, wind_speed=4.0, effective_height=30.0, sigma_y=50.0, sigma_z=20.0)

        # Non-positive sigmas
        with pytest.raises(ValueError, match="sigma_y and sigma_z must be strictly positive"):
            gaussian_plume_concentration(y=0.0, z=0.0, Q=10.0, wind_speed=4.0, effective_height=30.0, sigma_y=0.0, sigma_z=20.0)

        with pytest.raises(ValueError, match="sigma_y and sigma_z must be strictly positive"):
            gaussian_plume_concentration(y=0.0, z=0.0, Q=10.0, wind_speed=4.0, effective_height=30.0, sigma_y=50.0, sigma_z=-10.0)


class TestMassFluxConservation:
    """
    Test 13 — Analytical and numerical conservation of integrated advective mass flux.

    Mathematical Derivation:
    ------------------------
    Governing equation with ground reflection:
    C(y, z) = [ Q / (2 * pi * u * sy * sz) ] * exp(- y^2 / (2 * sy^2))
              * [ exp(- (z - H)^2 / (2 * sz^2)) + exp(- (z + H)^2 / (2 * sz^2)) ]

    Integrating over the semi-infinite vertical domain z in [0, inf) and horizontal domain y in (-inf, inf):
    Integral_y exp(- y^2 / (2 * sy^2)) dy = sqrt(2 * pi) * sy

    Integral_{z=0}^inf [ exp(- (z - H)^2 / (2 * sz^2)) + exp(- (z + H)^2 / (2 * sz^2)) ] dz
    = Integral_{-H}^inf exp(- zeta^2 / (2 * sz^2)) dzeta + Integral_{H}^inf exp(- xi^2 / (2 * sz^2)) dxi
    = Integral_{-inf}^inf exp(- zeta^2 / (2 * sz^2)) dzeta   (by symmetry of Gaussian tail)
    = sqrt(2 * pi) * sz

    Therefore:
    Total Mass Flux = Integral_{y=-inf}^inf Integral_{z=0}^inf [ u * C(y, z) ] dz dy
                    = u * [ Q / (2 * pi * u * sy * sz) ] * [ sqrt(2 * pi) * sy ] * [ sqrt(2 * pi) * sz ]
                    = Q
    """

    @pytest.mark.parametrize("H", [0.0, 25.0, 75.0])
    @pytest.mark.parametrize("stability", [StabilityClass.B, StabilityClass.D, StabilityClass.F])
    def test_integrated_mass_flux_conservation_quadrature(self, H, stability):
        """Verify that double numerical integration of u * C(y, z) over (y, z) domain equals Q."""
        Q = 100.0  # g/s
        u = 4.0    # m/s
        x = 1000.0 # m downwind

        sy, sz = compute_dispersion_coefficients(x, stability=stability, environment=EnvironmentType.RURAL)

        # Integration domain spanning 8 standard deviations (capturing > 99.999999% of Gaussian mass)
        y_limit = 8.0 * sy
        z_max = max(H + 8.0 * sz, 8.0 * sz)

        def integrand(z, y):
            c = gaussian_plume_concentration(
                y=y,
                z=z,
                Q=Q,
                wind_speed=u,
                effective_height=H,
                sigma_y=sy,
                sigma_z=sz,
                include_ground_reflection=True,
            )
            return u * c

        integrated_flux, abs_err = dblquad(
            integrand,
            -y_limit,
            y_limit,
            0.0,
            z_max,
            epsabs=1e-4,
            epsrel=1e-4,
        )

        # Total integrated flux should equal Q (100.0 g/s) within 0.01% numerical tolerance
        assert integrated_flux == pytest.approx(Q, rel=1e-4)

    def test_mass_flux_multi_domain_convergence(self):
        """
        Audit Test: Verify monotonic convergence of numerical mass flux integral toward Q
        as the integration domain size expands across k * sigma bounds (k = 2, 4, 6, 8).
        """
        Q = 100.0
        u = 5.0
        H = 40.0
        x = 1000.0

        sy, sz = compute_dispersion_coefficients(x, stability=StabilityClass.D, environment=EnvironmentType.RURAL)

        def integrand(z, y):
            c = gaussian_plume_concentration(
                y=y, z=z, Q=Q, wind_speed=u, effective_height=H, sigma_y=sy, sigma_z=sz, include_ground_reflection=True
            )
            return u * c

        fluxes = []
        multipliers = [2.0, 4.0, 6.0, 8.0]
        for k in multipliers:
            y_lim = k * sy
            z_lim = H + k * sz
            val, _ = dblquad(integrand, -y_lim, y_lim, 0.0, z_lim, epsabs=1e-5, epsrel=1e-5)
            fluxes.append(val)

        # 1. Fluxes must strictly increase with expanding domain
        for i in range(len(fluxes) - 1):
            assert fluxes[i] < fluxes[i + 1]

        # 2. k=2 captures ~95% of mass (erf(2/sqrt(2)) ~ 0.9545)
        assert fluxes[0] >= 0.90 * Q
        # 3. k=4 captures > 99.9% of mass
        assert fluxes[1] >= 0.999 * Q
        # 4. k=8 recovers Q to within 0.01% tolerance
        assert fluxes[3] == pytest.approx(Q, rel=1e-4)


class TestTextbookAnalyticalReferenceCases:
    """
    Test 14 — Independently derived analytical reference test cases evaluated from literature formulas.

    Each case records step-by-step analytical derivation with documented exact numerical values.
    """

    def test_reference_case_1_elevated_source_ground_centerline(self):
        """
        Reference Case 1: Elevated source, ground-level centerline receptor.
        -------------------------------------------------------------------
        Reference Scenario: Turner (1970) Workbook style standard elevated stack.
        Inputs:
            Q = 100.0 g/s
            u = 5.0 m/s
            H = 50.0 m
            x = 1000.0 m
            y = 0.0 m
            z = 0.0 m
            Stability = Class D (Rural)

        Step-by-step Analytical Derivation:
        1. sigma_y(1000 m) = 0.08 * 1000 / sqrt(1 + 0.0001 * 1000) = 80 / sqrt(1.1) = 76.27700713964738 m
        2. sigma_z(1000 m) = 0.06 * 1000 / sqrt(1 + 0.0015 * 1000) = 60 / sqrt(2.5) = 37.94733192202055 m
        3. Prefactor = Q / (2 * pi * u * sy * sz)
                    = 100 / (2 * pi * 5.0 * 76.27700713964738 * 37.94733192202055)
                    = 1.099689437e-3 g/m³
        4. Crosswind term = exp(- 0^2 / (2 * sy^2)) = 1.0
        5. Vertical term at z=0 = 2 * exp(- 50^2 / (2 * 37.94733192202055^2))
                                = 2 * exp(- 2500 / 2880.0)
                                = 2 * exp(- 0.8680555555555556)
                                = 2 * 0.419766023
                                = 0.839532047
        6. Expected Concentration = 1.099689437e-3 * 1.0 * 0.839532047
                                 = 9.232376242157e-4 g/m³
        """
        Q = 100.0
        u = 5.0
        H = 50.0
        x = 1000.0
        y = 0.0
        z = 0.0

        model = GaussianPlumeModel(
            Q=Q,
            wind_speed=u,
            effective_height=H,
            stability=StabilityClass.D,
            environment=EnvironmentType.RURAL,
        )

        expected_sy = 80.0 / np.sqrt(1.1)
        expected_sz = 60.0 / np.sqrt(2.5)
        expected_c = (
            (Q / (2.0 * np.pi * u * expected_sy * expected_sz))
            * 1.0
            * (2.0 * np.exp(-0.5 * (H / expected_sz) ** 2))
        )

        actual_c = model.evaluate(x=x, y=y, z=z)
        assert actual_c == pytest.approx(expected_c, rel=1e-10)
        assert actual_c == pytest.approx(9.232376242157e-4, rel=1e-6)

    def test_reference_case_2_ground_source_off_centerline(self):
        """
        Reference Case 2: Ground-level source (H=0), off-centerline receptor.
        ---------------------------------------------------------------------
        Reference Scenario: Surface release under convective unstable Class A conditions.
        Inputs:
            Q = 50.0 g/s
            u = 2.0 m/s
            H = 0.0 m
            x = 500.0 m
            y = 50.0 m
            z = 0.0 m
            Stability = Class A (Rural)

        Step-by-step Analytical Derivation:
        1. sigma_y(500 m) = 0.22 * 500 / sqrt(1 + 0.0001 * 500) = 110 / sqrt(1.05) = 107.34900802433864 m
        2. sigma_z(500 m) = 0.20 * 500 = 100.0 m
        3. Prefactor = 50 / (2 * pi * 2.0 * 107.34900802433864 * 100.0) = 3.706172559e-4 g/m³
        4. Crosswind term = exp(- 50^2 / (2 * 107.34900802433864^2)) = exp(- 2500 / 23047.61905) = exp(-0.108471074) = 0.897203657
        5. Vertical term at z=0, H=0 = 2 * exp(0) = 2.0
        6. Expected Concentration = 3.706172559e-4 * 0.897203657 * 2.0 = 6.650950434384e-4 g/m³
        """
        Q = 50.0
        u = 2.0
        H = 0.0
        x = 500.0
        y = 50.0
        z = 0.0

        model = GaussianPlumeModel(
            Q=Q,
            wind_speed=u,
            effective_height=H,
            stability=StabilityClass.A,
            environment=EnvironmentType.RURAL,
        )

        expected_sy = 110.0 / np.sqrt(1.05)
        expected_sz = 100.0
        expected_c = (
            (Q / (2.0 * np.pi * u * expected_sy * expected_sz))
            * np.exp(-0.5 * (y / expected_sy) ** 2)
            * 2.0
        )

        actual_c = model.evaluate(x=x, y=y, z=z)
        assert actual_c == pytest.approx(expected_c, rel=1e-10)
        assert actual_c == pytest.approx(6.650950434384e-4, rel=1e-6)

    def test_reference_case_3_elevated_3d_receptor(self):
        """
        Reference Case 3: Elevated 3D receptor point with ground reflection.
        -------------------------------------------------------------------
        Reference Scenario: Elevated source with elevated building/tower receptor.
        Inputs:
            Q = 250.0 g/s
            u = 4.0 m/s
            H = 60.0 m
            x = 2000.0 m
            y = 100.0 m
            z = 30.0 m
            Stability = Class C (Rural)

        Step-by-step Analytical Derivation:
        1. sigma_y(2000 m) = 0.11 * 2000 / sqrt(1 + 0.0001 * 2000) = 220 / sqrt(1.2) = 200.83160441856091 m
        2. sigma_z(2000 m) = 0.08 * 2000 / sqrt(1 + 0.0002 * 2000) = 160 / sqrt(1.4) = 135.22468075656266 m
        3. Prefactor = 250 / (2 * pi * 4.0 * 200.83160441856091 * 135.22468075656266) = 3.665777864e-4 g/m³
        4. Crosswind term = exp(- 100^2 / (2 * 200.83160441856091^2)) = exp(- 10000 / 80666.66667) = exp(-0.123966942) = 0.88340944
        5. Direct vertical term = exp(- (30 - 60)^2 / (2 * 135.22468075656266^2)) = exp(- 900 / 36571.42857) = exp(-0.024609375) = 0.97569077
        6. Reflected vertical term = exp(- (30 + 60)^2 / (2 * 135.22468075656266^2)) = exp(- 8100 / 36571.42857) = exp(-0.221484375) = 0.80132731
        7. Total vertical term = 0.97569077 + 0.80132731 = 1.77701808
        8. Expected Concentration = 3.665777864e-4 * 0.88340944 * 1.77701808 = 5.749977415853e-4 g/m³
        """
        Q = 250.0
        u = 4.0
        H = 60.0
        x = 2000.0
        y = 100.0
        z = 30.0

        model = GaussianPlumeModel(
            Q=Q,
            wind_speed=u,
            effective_height=H,
            stability=StabilityClass.C,
            environment=EnvironmentType.RURAL,
        )

        expected_sy = 220.0 / np.sqrt(1.2)
        expected_sz = 160.0 / np.sqrt(1.4)
        vert_direct = np.exp(-0.5 * ((z - H) / expected_sz) ** 2)
        vert_refl = np.exp(-0.5 * ((z + H) / expected_sz) ** 2)
        expected_c = (
            (Q / (2.0 * np.pi * u * expected_sy * expected_sz))
            * np.exp(-0.5 * (y / expected_sy) ** 2)
            * (vert_direct + vert_refl)
        )

        actual_c = model.evaluate(x=x, y=y, z=z)
        assert actual_c == pytest.approx(expected_c, rel=1e-10)
        assert actual_c == pytest.approx(5.749977415853e-4, rel=1e-6)
