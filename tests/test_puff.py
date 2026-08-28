"""
Comprehensive physical and numerical verification unit tests for Gaussian Puff Engine.

Verifies single-puff analytics, 3D mass conservation integrals, Lagrangian advection under
constant and variable wind fields, rotating wind analytical trajectories, wind reversal invariance,
source superposition, multi-timestep second-order convergence, and calm-wind numerical stability.
"""

import math
import pytest
import numpy as np
from scipy.integrate import simpson

from atmosim.physics.stability import StabilityClass
from atmosim.physics.dispersion import EnvironmentType
from atmosim.physics.puff import (
    EmissionSource,
    GaussianPuff,
    GaussianPuffConfig,
    GaussianPuffEngine,
    WindField,
    evaluate_single_puff_concentration,
    meteorological_wind_to_cartesian,
    cartesian_wind_to_meteorological,
)


class TestWindConversions:
    """Test meteorological to Cartesian wind vector conversions and reverse mappings."""

    def test_cardinal_meteorological_directions(self):
        """
        Verify meteorological wind direction mapping:
        * North wind (0°): blows from North -> South (u=0, v=-U)
        * East wind (90°): blows from East -> West (u=-U, v=0)
        * South wind (180°): blows from South -> North (u=0, v=+U)
        * West wind (270°): blows from West -> East (u=+U, v=0)
        """
        speed = 10.0

        # North wind
        u_n, v_n = meteorological_wind_to_cartesian(speed, 0.0)
        assert u_n == pytest.approx(0.0, abs=1e-7)
        assert v_n == pytest.approx(-10.0, abs=1e-7)

        # East wind
        u_e, v_e = meteorological_wind_to_cartesian(speed, 90.0)
        assert u_e == pytest.approx(-10.0, abs=1e-7)
        assert v_e == pytest.approx(0.0, abs=1e-7)

        # South wind
        u_s, v_s = meteorological_wind_to_cartesian(speed, 180.0)
        assert u_s == pytest.approx(0.0, abs=1e-7)
        assert v_s == pytest.approx(10.0, abs=1e-7)

        # West wind
        u_w, v_w = meteorological_wind_to_cartesian(speed, 270.0)
        assert u_w == pytest.approx(10.0, abs=1e-7)
        assert v_w == pytest.approx(0.0, abs=1e-7)

    def test_wind_round_trip(self):
        """Verify round-trip consistency between meteorological and Cartesian representations."""
        for deg in [0.0, 45.0, 90.0, 135.0, 220.0, 315.0]:
            u, v = meteorological_wind_to_cartesian(speed=8.5, direction_from_deg=deg)
            sp_rt, deg_rt = cartesian_wind_to_meteorological(u, v)
            assert sp_rt == pytest.approx(8.5, rel=1e-6)
            assert deg_rt == pytest.approx(deg, abs=1e-5)


class TestSinglePuffPhysics:
    """Test analytical properties of single Gaussian puff concentration evaluator."""

    def test_single_puff_center_maximum(self):
        """Puff concentration must be maximal at its spatial center (x_p, y_p, z_p)."""
        c_center = evaluate_single_puff_concentration(
            x_rec=100.0, y_rec=50.0, z_rec=30.0,
            puff_x=100.0, puff_y=50.0, puff_z=30.0,
            mass=500.0, sigma_x=20.0, sigma_y=20.0, sigma_z=10.0,
            include_ground_reflection=False,
        )
        c_off = evaluate_single_puff_concentration(
            x_rec=105.0, y_rec=55.0, z_rec=30.0,
            puff_x=100.0, puff_y=50.0, puff_z=30.0,
            mass=500.0, sigma_x=20.0, sigma_y=20.0, sigma_z=10.0,
            include_ground_reflection=False,
        )
        assert c_center > c_off

    def test_ground_reflection_doubling(self):
        """At z=0, the method-of-images reflection term exactly doubles ground concentration."""
        c_refl = evaluate_single_puff_concentration(
            x_rec=0.0, y_rec=0.0, z_rec=0.0,
            puff_x=0.0, puff_y=0.0, puff_z=25.0,
            mass=100.0, sigma_x=15.0, sigma_y=15.0, sigma_z=15.0,
            include_ground_reflection=True,
        )
        c_no_refl = evaluate_single_puff_concentration(
            x_rec=0.0, y_rec=0.0, z_rec=0.0,
            puff_x=0.0, puff_y=0.0, puff_z=25.0,
            mass=100.0, sigma_x=15.0, sigma_y=15.0, sigma_z=15.0,
            include_ground_reflection=False,
        )
        assert c_refl == pytest.approx(2.0 * c_no_refl, rel=1e-12)

    def test_puff_mass_conservation_3d_integral(self):
        """
        Verify that 3D spatial integration of puff concentration C(x, y, z) over the semi-infinite
        domain x in (-inf, inf), y in (-inf, inf), z in [0, inf) equals the total puff mass M:
        Integral Integral Integral C(x, y, z) dz dy dx = M
        """
        M = 250.0  # grams
        px, py, pz = 100.0, 50.0, 30.0
        sx, sy, sz = 25.0, 25.0, 15.0

        x_pts = np.linspace(px - 6 * sx, px + 6 * sx, 101)
        y_pts = np.linspace(py - 6 * sy, py + 6 * sy, 101)
        z_pts = np.linspace(0.0, pz + 6 * sz, 101)

        X, Y, Z = np.meshgrid(x_pts, y_pts, z_pts, indexing="ij")
        C = evaluate_single_puff_concentration(
            X, Y, Z,
            puff_x=px, puff_y=py, puff_z=pz,
            mass=M, sigma_x=sx, sigma_y=sy, sigma_z=sz,
            include_ground_reflection=True,
        )

        int_z = simpson(C, z_pts, axis=2)
        int_y = simpson(int_z, y_pts, axis=1)
        integrated_mass = simpson(int_y, x_pts, axis=0)

        # Recovers mass M to within Simpson quadrature precision (< 1e-6)
        assert integrated_mass == pytest.approx(M, rel=1e-6)

    def test_near_source_puff_growth_and_initial_sigma(self):
        """
        Verify near-source dispersion behavior (travel distance s < 100m):
        1. Finite initial sigma (sx0, sy0, sz0) prevents point singularities at release (s=0).
        2. Total sigma_y(s) = sqrt(sy0^2 + sy_turb(s)^2) is strictly >= sy0.
        3. Dispersion grows smoothly and continuously across the s = 100m boundary.
        """
        sx0, sy0, sz0 = 3.0, 3.0, 2.0
        src = EmissionSource(source_id="near_src", x=0, y=0, z=20, emission_rate=100, release_interval=100, initial_sigma=(sx0, sy0, sz0))
        wind = WindField.constant(u=5.0, v=0.0)

        engine = GaussianPuffEngine(config=GaussianPuffConfig(time_step=1.0))
        engine.add_source(src)

        # Step 1: t=0 -> release puff
        engine.step(1.0, wind)
        p = engine.active_puffs[0]

        # s = 5.0 m (< 100m)
        assert p.travel_distance == pytest.approx(5.0, abs=1e-5)
        assert p.sigma_x >= sx0
        assert p.sigma_y >= sy0
        assert p.sigma_z >= sz0
        assert np.isfinite(p.sigma_x)

        # Run until s = 150 m (crossing the 100m boundary)
        engine.run(duration=29.0, wind=wind, dt=1.0)
        assert p.travel_distance == pytest.approx(150.0, abs=1e-3)
        assert p.sigma_x > sx0
        assert p.sigma_y > sy0
        assert p.sigma_z > sz0


class TestLagrangianAdvection:
    """Test puff center motion under constant, rotating, and time-varying wind fields."""

    def test_constant_wind_trajectory(self):
        """Under uniform constant wind (u, v), puff center follows x(t) = x0 + u*t, y(t) = y0 + v*t."""
        u, v = 4.0, -3.0
        wind = WindField.constant(u=u, v=v)
        engine = GaussianPuffEngine(config=GaussianPuffConfig(time_step=2.0))
        engine.add_source(EmissionSource(source_id="s1", x=100.0, y=200.0, z=25.0, emission_rate=100.0, release_interval=10.0))

        # Advance 50 seconds
        engine.run(duration=50.0, wind=wind)

        # Find the first puff released at t=0 (current age = 50s)
        p0 = [p for p in engine.active_puffs if p.id == 1][0]
        expected_x = 100.0 + u * 50.0  # 300 m
        expected_y = 200.0 + v * 50.0  # 50 m

        assert p0.x == pytest.approx(expected_x, abs=1e-4)
        assert p0.y == pytest.approx(expected_y, abs=1e-4)

    def test_time_varying_wind_analytical_comparison(self):
        """
        Verify puff trajectory under time-varying wind u(t) = 2.0 + 0.1*t, v(t) = 1.0.
        Analytical trajectory: x(t) = x0 + 2*t + 0.05*t^2, y(t) = y0 + 1*t.
        """
        wind = WindField(
            u_func=lambda x, y, z, t: 2.0 + 0.1 * t,
            v_func=lambda x, y, z, t: 1.0,
        )
        engine = GaussianPuffEngine(config=GaussianPuffConfig(time_step=1.0))
        engine.add_source(EmissionSource(source_id="s1", x=0.0, y=0.0, z=10.0, emission_rate=50.0, release_interval=20.0))

        engine.run(duration=40.0, wind=wind)

        p0 = [p for p in engine.active_puffs if p.id == 1][0]
        t = 40.0
        expected_x = 2.0 * t + 0.05 * (t ** 2)  # 2*40 + 0.05*1600 = 80 + 80 = 160 m
        expected_y = 1.0 * t                   # 40 m

        assert p0.x == pytest.approx(expected_x, abs=1e-3)
        assert p0.y == pytest.approx(expected_y, abs=1e-3)

    def test_rotating_2d_wind_analytical_trajectory(self):
        """
        P2 Test: Automated numerical verification of puff trajectory under a rotating 2D wind field:
        u(t) = U * cos(omega * t), v(t) = U * sin(omega * t).
        Analytical trajectory from (0, 0):
        x(t) = (U / omega) * sin(omega * t)
        y(t) = - (U / omega) * (cos(omega * t) - 1)
        """
        U = 5.0        # m/s
        omega = 0.05   # rad/s (rotation period = 2*pi / 0.05 ~ 125.66 s)
        wind = WindField(
            u_func=lambda x, y, z, t: U * np.cos(omega * t),
            v_func=lambda x, y, z, t: U * np.sin(omega * t),
        )
        engine = GaussianPuffEngine(config=GaussianPuffConfig(time_step=0.5))
        engine.add_source(EmissionSource(source_id="s_rot", x=0.0, y=0.0, z=20.0, emission_rate=100.0, release_interval=100.0))

        duration = 50.0
        engine.run(duration=duration, wind=wind, dt=0.5)

        p = engine.active_puffs[0]
        x_analytical = (U / omega) * math.sin(omega * duration)
        y_analytical = -(U / omega) * (math.cos(omega * duration) - 1.0)

        assert p.x == pytest.approx(x_analytical, abs=0.01)  # error < 1 cm
        assert p.y == pytest.approx(y_analytical, abs=0.01)

    def test_wind_reversal_trajectory_preservation(self):
        """
        A wind reversal at t=T must not retroactively teleport or alter a puff's past trajectory.
        Wind blows East (u=+5, v=0) for 20s, then reverses West (u=-5, v=0) for 20s.
        The puff released at t=0 reaches x=100m at t=20s, then returns to x=0m at t=40s.
        """
        def u_reversal(x, y, z, t):
            return 5.0 if t < 20.0 else -5.0

        wind = WindField(u_func=u_reversal, v_func=lambda x, y, z, t: 0.0)
        engine = GaussianPuffEngine(config=GaussianPuffConfig(time_step=1.0))
        engine.add_source(EmissionSource(source_id="s1", x=0.0, y=0.0, z=10.0, emission_rate=100.0, release_interval=50.0))

        # Phase 1: t in [0, 20s]
        engine.run(duration=20.0, wind=wind)
        p0 = engine.active_puffs[0]
        assert p0.x == pytest.approx(100.0, abs=1e-4)

        # Phase 2: t in [20s, 40s] (reversed wind)
        engine.run(duration=20.0, wind=wind)
        assert p0.x == pytest.approx(0.0, abs=1e-3)


class TestEmissionMassAndSuperposition:
    """Test discrete mass creation Q*dt and multi-source linear superposition."""

    def test_discrete_mass_release_scaling(self):
        """Each puff must have mass Delta M = Q * dt_rel, and total released mass equals N * Q * dt_rel."""
        Q = 120.0  # g/s
        dt_rel = 10.0
        engine = GaussianPuffEngine(config=GaussianPuffConfig(time_step=5.0))
        engine.add_source(EmissionSource(source_id="s1", x=0, y=0, z=20, emission_rate=Q, release_interval=dt_rel))

        # Run 60 seconds -> exactly 6 releases
        engine.run(duration=60.0, wind=WindField.constant(2, 0))

        assert len(engine.active_puffs) == 6
        for p in engine.active_puffs:
            assert p.mass == pytest.approx(Q * dt_rel, rel=1e-12)  # 1200.0 g

        total_active_mass = sum(p.mass for p in engine.active_puffs)
        assert total_active_mass == pytest.approx(6 * 1200.0, rel=1e-12)

    def test_multi_source_linear_superposition(self):
        """
        Concentration from Source A + Source B evaluated simultaneously must exactly equal
        the sum of concentrations from Source A and Source B evaluated independently:
        C_{A+B}(x, y, z) = C_A(x, y, z) + C_B(x, y, z).
        """
        wind = WindField.constant(u=3.0, v=2.0)
        src_a = EmissionSource(source_id="A", x=-100.0, y=-50.0, z=20.0, emission_rate=80.0, release_interval=10.0)
        src_b = EmissionSource(source_id="B", x=50.0, y=100.0, z=30.0, emission_rate=120.0, release_interval=10.0)

        # Simulation with Source A only
        eng_a = GaussianPuffEngine(config=GaussianPuffConfig(time_step=5.0))
        eng_a.add_source(src_a)
        eng_a.run(duration=60.0, wind=wind)

        # Simulation with Source B only
        eng_b = GaussianPuffEngine(config=GaussianPuffConfig(time_step=5.0))
        eng_b.add_source(src_b)
        eng_b.run(duration=60.0, wind=wind)

        # Combined Simulation with Both Sources A + B
        eng_ab = GaussianPuffEngine(config=GaussianPuffConfig(time_step=5.0))
        eng_ab.add_source(src_a)
        eng_ab.add_source(src_b)
        eng_ab.run(duration=60.0, wind=wind)

        receptors_x = np.linspace(-200.0, 400.0, 20)
        receptors_y = np.linspace(-100.0, 400.0, 20)

        c_a = eng_a.evaluate(receptors_x, receptors_y, z_rec=0.0)
        c_b = eng_b.evaluate(receptors_x, receptors_y, z_rec=0.0)
        c_ab = eng_ab.evaluate(receptors_x, receptors_y, z_rec=0.0)

        np.testing.assert_allclose(c_ab, c_a + c_b, rtol=1e-12)


class TestNumericalStabilityAndConvergence:
    """Test calm wind stability, discretization convergence, and deterministic execution."""

    def test_calm_wind_stability(self):
        """
        Under calm conditions (u=0, v=0), the engine must remain numerically stable without NaN/Inf,
        and puff dispersion must continue growing based on turbulent diffusion time scaling.
        """
        wind = WindField.constant(u=0.0, v=0.0)
        engine = GaussianPuffEngine(config=GaussianPuffConfig(time_step=5.0, calm_wind_threshold=0.1))
        engine.add_source(EmissionSource(source_id="s1", x=0, y=0, z=20, emission_rate=100.0, release_interval=10.0))

        engine.run(duration=50.0, wind=wind)

        assert len(engine.active_puffs) > 0
        p0 = engine.active_puffs[0]
        # Position should stay at source
        assert p0.x == pytest.approx(0.0, abs=1e-7)
        assert p0.y == pytest.approx(0.0, abs=1e-7)

        # Dispersion must have grown stably (finite, positive)
        assert p0.sigma_x > 1.0
        assert p0.sigma_y > 1.0
        assert p0.sigma_z > 1.0
        assert math.isfinite(p0.sigma_x)

        # Receptor evaluation must be finite and positive
        c = engine.evaluate(x_rec=np.linspace(-50, 50, 10), y_rec=np.zeros(10), z_rec=0.0)
        assert np.all(np.isfinite(c))
        assert np.all(c >= 0.0)

    def test_multi_timestep_order_of_convergence(self):
        """
        P2 Test: Multi-timestep trajectory convergence test across dt in [20, 10, 5, 2, 1, 0.5] seconds.
        Verifies monotonic error reduction and O(dt^2) second-order midpoint convergence against analytical trajectory.
        """
        U = 5.0
        omega = 0.05
        wind = WindField(
            u_func=lambda x, y, z, t: U * np.cos(omega * t),
            v_func=lambda x, y, z, t: U * np.sin(omega * t),
        )
        duration = 60.0
        x_analytical = (U / omega) * math.sin(omega * duration)
        y_analytical = -(U / omega) * (math.cos(omega * duration) - 1.0)

        timesteps = [20.0, 10.0, 5.0, 2.0, 1.0, 0.5]
        errors = []

        for dt in timesteps:
            eng = GaussianPuffEngine(config=GaussianPuffConfig(time_step=dt))
            eng.add_source(EmissionSource(source_id="s_conv", x=0, y=0, z=20, emission_rate=100, release_interval=100.0))
            eng.run(duration=duration, wind=wind, dt=dt)
            p = eng.active_puffs[0]
            err = math.hypot(p.x - x_analytical, p.y - y_analytical)
            errors.append(err)

        # 1. Error must decrease monotonically across all refined timesteps
        for i in range(len(errors) - 1):
            assert errors[i] > errors[i + 1], f"Monotonic convergence failed at dt={timesteps[i]}: {errors[i]} <= {errors[i+1]}"

        # 2. Second-order scaling: when dt is halved from 10s to 5s, error drops by ~factor of 4 (O(dt^2))
        err_10 = errors[1]
        err_5 = errors[2]
        ratio = err_10 / err_5
        assert 3.5 <= ratio <= 4.5  # ~4.0 for second-order midpoint

        # 3. Discrepancy at dt=0.5s is sub-centimeter (< 0.01 m)
        assert errors[-1] < 0.01

    def test_deterministic_execution(self):
        """Identical simulation configurations must yield bit-exact identical concentration fields."""
        wind = WindField.constant(u=3.5, v=1.2)
        source = EmissionSource(source_id="s", x=50, y=50, z=25, emission_rate=150, release_interval=10.0)

        eng1 = GaussianPuffEngine(config=GaussianPuffConfig(time_step=5.0))
        eng1.add_source(source)
        eng1.run(duration=50.0, wind=wind)
        c1 = eng1.evaluate(np.linspace(0, 200, 30), np.linspace(0, 200, 30))

        eng2 = GaussianPuffEngine(config=GaussianPuffConfig(time_step=5.0))
        eng2.add_source(source)
        eng2.run(duration=50.0, wind=wind)
        c2 = eng2.evaluate(np.linspace(0, 200, 30), np.linspace(0, 200, 30))

        np.testing.assert_array_equal(c1, c2)
