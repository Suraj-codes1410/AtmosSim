"""
Time-Dependent Gaussian Puff Dispersion Engine for AtmosSim.

Implements Lagrangian puff advection, variable wind transport, dynamic dispersion growth,
puff lifecycle management, multi-source release, and vectorized receptor concentration superposition.

Governing Equation
------------------
For an active puff parcel of mass M(t) at center position (x_p, y_p, z_p) with dispersion
standard deviations (sigma_x, sigma_y, sigma_z) and method-of-images ground reflection:

C(x, y, z, t) = [ M(t) / ((2*pi)^(3/2) * sigma_x * sigma_y * sigma_z) ]
                * exp( - (x - x_p)^2 / (2 * sigma_x^2) )
                * exp( - (y - y_p)^2 / (2 * sigma_y^2) )
                * [ exp( - (z - z_p)^2 / (2 * sigma_z^2) ) + exp( - (z + z_p)^2 / (2 * sigma_z^2) ) ]

Physical Approximations & Numerical Regularizations
---------------------------------------------------
1. Horizontal Isotropy Approximation:
   sigma_x(t) = sigma_y(t) is adopted following statistical turbulence theory for isotropic
   horizontal eddies within the planetary boundary layer (Taylor, 1921; Batchelor, 1950, 1952;
   Gifford, 1976) and standard regulatory Gaussian puff modeling conventions (CALPUFF, Scire et al., 2000;
   Zannetti, 1990). Longitudinal shear-stretching is neglected in standard isotropic Gaussian puffs.
2. Equivalent Cumulative Travel Distance Approach:
   For variable winds, dispersion widths sigma_y(s), sigma_z(s) grow as functions of the integrated
   Lagrangian path length s(t) = int |u(t')| dt' via the virtual distance / equivalent path length
   method (Ludwig et al., 1977; Zannetti, 1990). Inherited Briggs empirical validity range is 100m <= s <= 10000m.
3. Numerical Regularization for Calm Winds:
   u_min = 0.1 m/s and s_eff = max(s(t), u_min * age, 1.0 m) are NUMERICAL REGULARIZATIONS (engineering safeguards)
   designed to prevent zero-division singularities and numerical freeze during near-zero advection,
   NOT fundamental physical laws.
4. Spatial Wind Uniformity in Phase 1:
   Phase 1 assumes a spatially uniform horizontal wind vector U(t) = (u(t), v(t)) across the local domain
   during each timestep. Spatially non-uniform / gridded meteorological wind fields are introduced in later phases.

References
----------
1. Turner, D. B. (1970). Workbook of Atmospheric Dispersion Estimates.
   U.S. EPA Office of Air Programs Publication No. AP-26. Chapter 5: Instantaneous Releases.
2. Seinfeld, J. H., & Pandis, S. N. (2016). Atmospheric Chemistry and Physics:
   From Air Pollution to Climate Change (3rd ed.). John Wiley & Sons. Chapter 18, Eq. 18.52-18.58.
3. Scire, J. S., Strimaitis, D. G., & Yamartino, R. J. (2000). A User's Guide for the
   CALPUFF Dispersion Model. Earth Tech, Inc., Concord, MA. Section 2.1.
4. Gifford, F. A. (1976). Turbulent diffusion-typing schemes: A review.
   Nuclear Safety, 17(1), 68-86.
5. Taylor, G. I. (1921). Diffusion by continuous movements.
   Proceedings of the London Mathematical Society, 2(1), 196-212.
6. Batchelor, G. K. (1950). The application of the similarity theory of turbulence to atmospheric diffusion.
   Quarterly Journal of the Royal Meteorological Society, 76(328), 133-146.
7. Zannetti, P. (1990). Air Pollution Modeling: Theories, Computational Methods and Available Software.
   Computational Mechanics Publications / Van Nostrand Reinhold. Chapter 6.
8. Ludwig, F. L., Gasiorek, L. S., & Ruff, R. E. (1977). Simplification of a Gaussian puff model for
   real-time minicomputer use. Atmospheric Environment, 11(5), 431-436.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple, Union
import math
import numpy as np

from atmosim.physics.stability import StabilityClass
from atmosim.physics.dispersion import (
    EnvironmentType,
    compute_sigma_y,
    compute_sigma_z,
)
from atmosim.physics.puff_lifecycle import (
    PuffLifecycleConfig,
    PuffLifecycleState,
    PuffCullReason,
    PuffLifecycleStats,
    evaluate_cull_condition,
)


def meteorological_wind_to_cartesian(
    speed: float,
    direction_from_deg: float,
) -> Tuple[float, float]:
    """
    Convert meteorological wind (speed, direction FROM which wind blows)
    to local Cartesian velocity components (u=Eastward, v=Northward) in m/s.

    Parameters
    ----------
    speed : float
        Horizontal wind speed in m/s (>= 0).
    direction_from_deg : float
        Meteorological wind direction in degrees clockwise from North (0° to 360°).
        0° = North wind (blows from North toward South).
        90° = East wind (blows from East toward West).
        180° = South wind (blows from South toward North).
        270° = West wind (blows from West toward East).

    Returns
    -------
    Tuple[float, float]
        (u, v) in m/s where +u is Eastward and +v is Northward.
    """
    if speed < 0.0:
        raise ValueError(f"Wind speed must be non-negative, got {speed}")
    
    # Wind vector points in the direction TOWARD which air moves (theta_to = theta_from + 180)
    theta_rad = math.radians(direction_from_deg)
    u = -speed * math.sin(theta_rad)
    v = -speed * math.cos(theta_rad)
    return u, v


def cartesian_wind_to_meteorological(u: float, v: float) -> Tuple[float, float]:
    """
    Convert Cartesian velocity components (u=Eastward, v=Northward) to meteorological (speed, direction_from_deg).

    Parameters
    ----------
    u : float
        Eastward velocity in m/s.
    v : float
        Northward velocity in m/s.

    Returns
    -------
    Tuple[float, float]
        (speed in m/s, direction_from in degrees [0, 360))
    """
    speed = math.hypot(u, v)
    if speed < 1e-9:
        return 0.0, 0.0
    # Meteorological direction is direction FROM which wind blows
    dir_to_rad = math.atan2(u, v)  # angle from North clockwise
    dir_from_deg = (math.degrees(dir_to_rad) + 180.0) % 360.0
    return speed, dir_from_deg


@dataclass
class WindField:
    """
    Representation of a spatial-temporal horizontal wind velocity field.
    In Phase 1, spatial uniformity is assumed across the local computational domain.
    """
    u_func: Callable[[float, float, float, float], float]
    v_func: Callable[[float, float, float, float], float]

    @classmethod
    def constant(cls, u: float, v: float) -> "WindField":
        """Create spatially and temporally uniform constant wind field."""
        return cls(
            u_func=lambda x, y, z, t: float(u),
            v_func=lambda x, y, z, t: float(v),
        )

    @classmethod
    def from_meteorological(cls, speed: float, direction_from_deg: float) -> "WindField":
        """Create constant wind field from meteorological speed and direction."""
        u, v = meteorological_wind_to_cartesian(speed, direction_from_deg)
        return cls.constant(u, v)

    def get_velocity(self, x: float, y: float, z: float, t: float) -> Tuple[float, float]:
        """Query horizontal wind velocity (u, v) in m/s at coordinates (x, y, z) and time t."""
        return self.u_func(x, y, z, t), self.v_func(x, y, z, t)


@dataclass(frozen=True)
class EmissionSource:
    """
    Continuous or time-varying point emission source for Gaussian puff generation.

    Parameters
    ----------
    source_id : str
        Unique identifier for the emission source.
    x, y, z : float
        3D Cartesian coordinates of source in meters (+x=East, +y=North, z=effective release height H).
    emission_rate : float or Callable[[float], float]
        Pollutant emission rate Q in g/s (mass per unit time). Can be constant float or time function Q(t).
    release_interval : float, default=10.0
        Puff generation interval Delta t in seconds.
    initial_sigma : Tuple[float, float, float], default=(1.0, 1.0, 1.0)
        Initial finite puff dimensions (sigma_x0, sigma_y0, sigma_z0) in meters.
    """
    source_id: str
    x: float
    y: float
    z: float  # Release height H
    emission_rate: Union[float, Callable[[float], float]] = 100.0
    release_interval: float = 10.0
    initial_sigma: Tuple[float, float, float] = (1.0, 1.0, 1.0)

    def __post_init__(self):
        if self.z < 0.0:
            raise ValueError(f"Source release height z (H) must be non-negative, got {self.z}")
        if self.release_interval <= 0.0:
            raise ValueError(f"release_interval must be strictly positive, got {self.release_interval}")
        if any(s <= 0.0 for s in self.initial_sigma):
            raise ValueError(f"initial_sigma components must be strictly positive, got {self.initial_sigma}")

    def get_emission_rate(self, t: float) -> float:
        """Evaluate emission rate Q(t) in g/s at time t."""
        if callable(self.emission_rate):
            q = float(self.emission_rate(t))
        else:
            q = float(self.emission_rate)
        if q < 0.0:
            raise ValueError(f"Emission rate must be non-negative, got {q} at time {t}")
        return q


@dataclass
class GaussianPuff:
    """
    Individual Lagrangian Gaussian puff parcel representing a finite mass of pollutant.
    """
    id: int
    source_id: str
    release_time: float
    release_pos: Tuple[float, float, float]
    mass: float  # Current pollutant mass in grams
    x: float     # Current Cartesian x (m)
    y: float     # Current Cartesian y (m)
    z: float     # Current Cartesian z (m)
    sigma_x: float
    sigma_y: float
    sigma_z: float
    travel_distance: float = 0.0  # Cumulative travel distance s(t) in meters
    age: float = 0.0              # Current age (t - release_time) in seconds
    state: PuffLifecycleState = PuffLifecycleState.CREATED
    cull_reason: PuffCullReason = PuffCullReason.NONE


@dataclass(frozen=True)
class GaussianPuffConfig:
    """
    Global configuration parameters for the Gaussian Puff dispersion engine.

    Parameters
    ----------
    time_step : float, default=5.0
        Advection integration step in seconds.
    stability : StabilityClass, default=StabilityClass.D
        Atmospheric stability class for dispersion growth.
    environment : EnvironmentType, default=EnvironmentType.RURAL
        Surface roughness regime (RURAL or URBAN).
    calm_wind_threshold : float, default=0.1
        Numerical regularization threshold u_min in m/s preventing zero-division singularity.
    include_ground_reflection : bool, default=True
        Include method-of-images specular ground reflection term.
    mass_decay_rate : float, default=0.0
        Exponential loss rate lambda in 1/s (0.0 for conservative passive tracer).
    lifecycle_config : PuffLifecycleConfig
        Rules governing computational domain culling.
    """
    time_step: float = 5.0
    stability: StabilityClass = StabilityClass.D
    environment: EnvironmentType = EnvironmentType.RURAL
    calm_wind_threshold: float = 0.1  # Numerical regularization (m/s)
    include_ground_reflection: bool = True
    mass_decay_rate: float = 0.0  # lambda in 1/s (0.0 for conservative passive tracer)
    lifecycle_config: PuffLifecycleConfig = field(default_factory=PuffLifecycleConfig)

    def __post_init__(self):
        if self.time_step <= 0.0:
            raise ValueError(f"time_step must be strictly positive, got {self.time_step}")
        if self.calm_wind_threshold <= 0.0:
            raise ValueError(f"calm_wind_threshold must be strictly positive, got {self.calm_wind_threshold}")
        if self.mass_decay_rate < 0.0:
            raise ValueError(f"mass_decay_rate must be non-negative, got {self.mass_decay_rate}")


def evaluate_single_puff_concentration(
    x_rec: Union[float, np.ndarray],
    y_rec: Union[float, np.ndarray],
    z_rec: Union[float, np.ndarray],
    puff_x: float,
    puff_y: float,
    puff_z: float,
    mass: float,
    sigma_x: float,
    sigma_y: float,
    sigma_z: float,
    include_ground_reflection: bool = True,
) -> Union[float, np.ndarray]:
    """
    Evaluate concentration contribution of a single Gaussian puff parcel at receptor point(s).

    Parameters
    ----------
    x_rec, y_rec, z_rec : float or np.ndarray
        Receptor coordinates in meters.
    puff_x, puff_y, puff_z : float
        Puff center coordinates in meters.
    mass : float
        Puff mass in grams.
    sigma_x, sigma_y, sigma_z : float
        Puff dispersion standard deviations in meters.
    include_ground_reflection : bool, default=True
        Include method-of-images surface reflection term.

    Returns
    -------
    float or np.ndarray
        Mass concentration in g/m³.
    """
    if mass <= 0.0:
        return 0.0 if np.isscalar(x_rec) else np.zeros_like(x_rec, dtype=np.float64)

    if sigma_x <= 0.0 or sigma_y <= 0.0 or sigma_z <= 0.0:
        raise ValueError(
            f"Puff dispersion widths must be strictly positive, got sx={sigma_x}, sy={sigma_y}, sz={sigma_z}"
        )

    is_scalar = np.isscalar(x_rec) and np.isscalar(y_rec) and np.isscalar(z_rec)
    x_arr = np.asanyarray(x_rec, dtype=np.float64)
    y_arr = np.asanyarray(y_rec, dtype=np.float64)
    z_arr = np.asanyarray(z_rec, dtype=np.float64)

    # Normalization prefactor: M / ((2*pi)^(3/2) * sx * sy * sz)
    norm = mass / ((2.0 * np.pi) ** 1.5 * sigma_x * sigma_y * sigma_z)

    # Horizontal Gaussian kernels
    dx = (x_arr - puff_x) / sigma_x
    dy = (y_arr - puff_y) / sigma_y
    h_kernel = np.exp(-0.5 * (dx * dx + dy * dy))

    # Vertical Gaussian kernels (direct + ground reflection)
    dz_direct = (z_arr - puff_z) / sigma_z
    v_direct = np.exp(-0.5 * dz_direct * dz_direct)

    if include_ground_reflection:
        dz_refl = (z_arr + puff_z) / sigma_z
        v_refl = np.exp(-0.5 * dz_refl * dz_refl)
        v_kernel = v_direct + v_refl
    else:
        v_kernel = v_direct

    c = norm * h_kernel * v_kernel
    return float(c) if is_scalar else c


class GaussianPuffEngine:
    """
    Time-dependent Gaussian Puff dispersion simulator.

    Manages multi-source puff generation, advection through variable wind fields,
    dynamic dispersion growth, lifecycle culling, and vectorized receptor concentration evaluation.
    """

    def __init__(self, config: Optional[GaussianPuffConfig] = None) -> None:
        self.config = config if config is not None else GaussianPuffConfig()
        self.sources: List[EmissionSource] = []
        self.active_puffs: List[GaussianPuff] = []
        self.culled_puffs: List[GaussianPuff] = []
        self.stats = PuffLifecycleStats()
        self.current_time: float = 0.0
        self._next_puff_id: int = 1
        self._source_last_release: Dict[str, float] = {}

    def add_source(self, source: EmissionSource) -> None:
        """Register a new emission point source."""
        self.sources.append(source)
        self._source_last_release[source.source_id] = -1e9

    def reset(self) -> None:
        """Reset simulation state and clear all puff populations."""
        self.active_puffs.clear()
        self.culled_puffs.clear()
        self.stats = PuffLifecycleStats()
        self.current_time = 0.0
        self._next_puff_id = 1
        for src_id in self._source_last_release:
            self._source_last_release[src_id] = -1e9

    def _create_puffs(self, t: float) -> None:
        """Generate new discrete puff parcels from active sources."""
        for src in self.sources:
            last_t = self._source_last_release.get(src.source_id, -1e9)
            if t >= last_t + src.release_interval - 1e-9:
                dt_rel = src.release_interval
                q = src.get_emission_rate(t)
                mass = q * dt_rel  # Delta M = Q * Delta t

                sx0, sy0, sz0 = src.initial_sigma
                puff = GaussianPuff(
                    id=self._next_puff_id,
                    source_id=src.source_id,
                    release_time=t,
                    release_pos=(src.x, src.y, src.z),
                    mass=mass,
                    x=src.x,
                    y=src.y,
                    z=src.z,
                    sigma_x=sx0,
                    sigma_y=sy0,
                    sigma_z=sz0,
                    travel_distance=0.0,
                    age=0.0,
                    state=PuffLifecycleState.ACTIVE,
                )
                self.active_puffs.append(puff)
                self.stats.record_creation(1)
                self._next_puff_id += 1
                self._source_last_release[src.source_id] = t

    def _update_puffs(self, dt: float, wind: WindField) -> None:
        """
        Advect active puffs, compute dispersion growth, apply mass decay, and check culling.
        """
        surviving_puffs: List[GaussianPuff] = []

        for puff in self.active_puffs:
            # 1. Wind velocity integration (second-order midpoint evaluation)
            u1, v1 = wind.get_velocity(puff.x, puff.y, puff.z, self.current_time)
            mid_x = puff.x + 0.5 * u1 * dt
            mid_y = puff.y + 0.5 * v1 * dt
            u_mid, v_mid = wind.get_velocity(mid_x, mid_y, puff.z, self.current_time + 0.5 * dt)

            # Advect puff center
            puff.x += u_mid * dt
            puff.y += v_mid * dt
            puff.age += dt

            speed = math.hypot(u_mid, v_mid)
            puff.travel_distance += speed * dt

            # 2. Dynamic dispersion growth
            # Numerical regularization: s_eff = max(s, u_min * age, 1.0 m) prevents division-by-zero
            s_eff = max(puff.travel_distance, self.config.calm_wind_threshold * puff.age, 1.0)

            # Briggs parameterizations for rural/urban dispersion
            sy_growth = compute_sigma_y(s_eff, self.config.stability, self.config.environment)
            sz_growth = compute_sigma_z(s_eff, self.config.stability, self.config.environment)

            # Horizontal isotropic dispersion approximation: sigma_x = sigma_y (Taylor 1921, Gifford 1976, CALPUFF)
            sx_growth = sy_growth

            sx0, sy0, sz0 = (1.0, 1.0, 1.0)
            for src in self.sources:
                if src.source_id == puff.source_id:
                    sx0, sy0, sz0 = src.initial_sigma
                    break

            puff.sigma_x = math.hypot(sx0, float(sx_growth))
            puff.sigma_y = math.hypot(sy0, float(sy_growth))
            puff.sigma_z = math.hypot(sz0, float(sz_growth))

            # 3. Mass decay (if enabled)
            if self.config.mass_decay_rate > 0.0:
                puff.mass *= math.exp(-self.config.mass_decay_rate * dt)

            # 4. Lifecycle computational culling check
            should_cull, reason = evaluate_cull_condition(
                age=puff.age,
                x=puff.x,
                y=puff.y,
                z=puff.z,
                mass=puff.mass,
                source_x=puff.release_pos[0],
                source_y=puff.release_pos[1],
                config=self.config.lifecycle_config,
            )

            if should_cull:
                puff.state = PuffLifecycleState.CULLED
                puff.cull_reason = reason
                self.culled_puffs.append(puff)
                self.stats.record_cull(reason, 1)
            else:
                surviving_puffs.append(puff)

        self.active_puffs = surviving_puffs

    def step(self, dt: float, wind: WindField) -> None:
        """Advance simulation state by single timestep dt."""
        self._create_puffs(self.current_time)
        self._update_puffs(dt, wind)
        self.current_time += dt

    def run(
        self,
        duration: float,
        wind: WindField,
        dt: Optional[float] = None,
    ) -> None:
        """
        Execute simulation for specified duration in seconds.

        Parameters
        ----------
        duration : float
            Total simulation time window in seconds.
        wind : WindField
            Wind vector field.
        dt : float, optional
            Integration timestep in seconds. If None, uses config.time_step.
        """
        step_dt = dt if dt is not None else self.config.time_step
        n_steps = int(math.ceil(duration / step_dt))

        for _ in range(n_steps):
            self.step(step_dt, wind)

    def evaluate(
        self,
        x_rec: Union[float, np.ndarray],
        y_rec: Union[float, np.ndarray],
        z_rec: Union[float, np.ndarray] = 0.0,
    ) -> Union[float, np.ndarray]:
        """
        Evaluate total mass concentration at given receptor coordinates via puff superposition.

        Parameters
        ----------
        x_rec, y_rec : float or np.ndarray
            Receptor Cartesian coordinates in meters.
        z_rec : float or np.ndarray, default=0.0
            Receptor height above ground in meters.

        Returns
        -------
        float or np.ndarray
            Superimposed concentration in g/m³.
        """
        is_scalar = np.isscalar(x_rec) and np.isscalar(y_rec) and np.isscalar(z_rec)

        if not self.active_puffs:
            return 0.0 if is_scalar else np.zeros_like(x_rec, dtype=np.float64)

        x_arr = np.asanyarray(x_rec, dtype=np.float64)
        y_arr = np.asanyarray(y_rec, dtype=np.float64)
        z_arr = np.asanyarray(z_rec, dtype=np.float64)

        orig_shape = x_arr.shape
        x_flat = x_arr.ravel()
        y_flat = y_arr.ravel()
        z_flat = np.broadcast_to(z_arr, orig_shape).ravel()

        n_rec = len(x_flat)
        total_conc = np.zeros(n_rec, dtype=np.float64)

        # Vectorized evaluation over active puffs in batches
        batch_size = 256
        n_puffs = len(self.active_puffs)

        for p_start in range(0, n_puffs, batch_size):
            p_end = min(p_start + batch_size, n_puffs)
            batch = self.active_puffs[p_start:p_end]

            px = np.array([p.x for p in batch])
            py = np.array([p.y for p in batch])
            pz = np.array([p.z for p in batch])
            pm = np.array([p.mass for p in batch])
            psx = np.array([p.sigma_x for p in batch])
            psy = np.array([p.sigma_y for p in batch])
            psz = np.array([p.sigma_z for p in batch])

            norm = pm / ((2.0 * np.pi) ** 1.5 * psx * psy * psz)

            dx = (x_flat[np.newaxis, :] - px[:, np.newaxis]) / psx[:, np.newaxis]
            dy = (y_flat[np.newaxis, :] - py[:, np.newaxis]) / psy[:, np.newaxis]
            h_term = np.exp(-0.5 * (dx * dx + dy * dy))

            dz_d = (z_flat[np.newaxis, :] - pz[:, np.newaxis]) / psz[:, np.newaxis]
            v_d = np.exp(-0.5 * dz_d * dz_d)

            if self.config.include_ground_reflection:
                dz_r = (z_flat[np.newaxis, :] + pz[:, np.newaxis]) / psz[:, np.newaxis]
                v_r = np.exp(-0.5 * dz_r * dz_r)
                v_term = v_d + v_r
            else:
                v_term = v_d

            puff_concs = norm[:, np.newaxis] * h_term * v_term
            total_conc += np.sum(puff_concs, axis=0)

        if is_scalar:
            return float(total_conc[0])
        return total_conc.reshape(orig_shape)
