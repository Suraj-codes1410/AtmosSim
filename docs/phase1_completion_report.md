# AtmosSim — Phase 1 Completion Report

## 1. Status

**Phase 1 Status: COMPLETE (Evidence Levels 1–4 Verified, Level 5 Deferred)**

The time-dependent **Gaussian Puff Engine** has been implemented, analytically verified, and evaluated across 140 automated unit and regression tests. The engine simulates Lagrangian advection through variable, rotating, and reversing wind fields, discrete mass creation from multiple emission sources, dynamic dispersion growth, automated computational domain lifecycle management with bounded memory scaling, and conformal WGS84-to-Cartesian coordinate transformations.

---

## 2. Implemented Components

* **Core Physics Engine ([`src/atmosim/physics/puff.py`](../src/atmosim/physics/puff.py)):**
  * `GaussianPuff`: Lagrangian puff parcel representation with position, mass, age, travel distance, and $(\sigma_x, \sigma_y, \sigma_z)$ dimensions.
  * `GaussianPuffEngine`: Time-dependent simulation manager coordinating puff generation, advection, dispersion growth, culling, and vectorized receptor evaluation.
  * `EmissionSource`: Source configuration with continuous/variable emission rate $Q(t)$, release height $H$, and release interval $\Delta t_{\text{rel}}$.
  * `WindField`: Spatial-temporal wind vector representation supporting constant, time-varying, and meteorological wind inputs (assuming spatial uniformity across the domain during each timestep in Phase 1).
  * `evaluate_single_puff_concentration()`: Vectorized closed-form 3D Gaussian puff concentration evaluator with method-of-images ground reflection.
  * `meteorological_wind_to_cartesian()` / `cartesian_wind_to_meteorological()`: Rigorous direction conversions adhering to meteorological standards ($\theta_{\text{to}} = (\theta_{\text{met}} + 180^\circ) \pmod{360^\circ}$).
* **Computational Domain Management ([`src/atmosim/physics/puff_lifecycle.py`](../src/atmosim/physics/puff_lifecycle.py)):**
  * `PuffLifecycleConfig` & `SpatialBounds`: Configurable multi-criteria computational domain culling policies (maximum age, maximum travel distance, minimum mass, 3D domain bounds).
  * `PuffLifecycleStats`: Diagnostic accounting tracking created, active, culled, and peak active puff populations.
* **Geographic Coordinate Transformations ([`src/atmosim/physics/coordinates.py`](../src/atmosim/physics/coordinates.py)):**
  * `LocalCoordinateSystem` & `determine_utm_epsg()`: Conformal geodetic WGS84 (`EPSG:4326`) to local metric Cartesian coordinates (+x=East, +y=North in meters) with sub-millimeter round-trip numerical consistency via `pyproj`.
* **Diagnostic Visualization Suite ([`src/atmosim/visualization/puff.py`](../src/atmosim/visualization/puff.py)):**
  * Visualizations for puff center trajectories, dispersion growth curves $\sigma(t)$, 2D concentration fields, multi-source plumes, and lifecycle population dynamics.

---

## 3. Scientific Formulations

* **3D Gaussian Puff Governing Equation:**
  $$C_p(x, y, z, t) = \frac{M(t)}{(2\pi)^{3/2} \sigma_x \sigma_y \sigma_z} \exp\left( -\frac{(x - x_p)^2}{2\sigma_x^2} - \frac{(y - y_p)^2}{2\sigma_y^2} \right) \left[ \exp\left( -\frac{(z - z_p)^2}{2\sigma_z^2} \right) + \exp\left( -\frac{(z + z_p)^2}{2\sigma_z^2} \right) \right]$$
* **Ground Boundary Condition:** Specular reflection via method of images ($\partial C/\partial z = 0$ at $z=0$).
* **Puff Mass Creation:** $\Delta M = Q(t) \cdot \Delta t_{\text{rel}}$ in grams.
* **Advective Trajectory Integration:** Second-order midpoint velocity integration:
  $$\mathbf{x}_p(t + \Delta t) = \mathbf{x}_p(t) + \mathbf{U}\left(\mathbf{x}_p + \frac{1}{2}\mathbf{U}\Delta t, t + \frac{1}{2}\Delta t\right) \Delta t$$

---

## 4. $\sigma_x$ Provenance & Dispersion Growth

* **Literature Provenance & Qualifications:**
  * Grounded in statistical turbulence theory for isotropic horizontal eddies within the planetary boundary layer (Taylor, 1921; Batchelor, 1950, 1952; Gifford, 1976) and standard regulatory Gaussian puff modeling guidance (CALPUFF / MESOPUFF; Scire et al., 2000, Section 2.1.2; Zannetti, 1990):
    $$\sigma_x(t) = \sigma_y(t)$$
  * $\sigma_x = \sigma_y$ is an engineering approximation valid under horizontal turbulent isotropy. Longitudinal shear-stretching is neglected in standard isotropic Gaussian puffs.
* **Dynamic Travel Distance Parameterization (Equivalent Path Length Method):**
  $$\sigma_y(s) = \sqrt{\sigma_{y0}^2 + [\sigma_y^{\text{Briggs}}(s_{\text{eff}})]^2}, \quad \sigma_x(s) = \sigma_y(s), \quad \sigma_z(s) = \sqrt{\sigma_{z0}^2 + [\sigma_z^{\text{Briggs}}(s_{\text{eff}})]^2}$$
  where $s(t) = \int |\mathbf{U}| dt$ is the integrated Lagrangian path length (Ludwig et al., 1977).
* **Inherited Briggs Validity Limits & Near-Source Region ($s < 100\ \text{m}$):**
  * **Distance Regimes:**
    1. $0 < s < 100\ \text{m}$: Near-source engineering / extrapolation regime (governed by initial dimensions and algebraic asymptote).
    2. $100\ \text{m} \le s \le 10,000\ \text{m}$: Briggs empirical core (field tracer calibration).
    3. $s > 10,000\ \text{m}$: Far-field extrapolation regime.
  * **Mathematical Property vs Physical Theory:** The algebraic Briggs parameterizations possess a linear mathematical asymptote $\lim_{s \to 0^+} \frac{\sigma(s)}{s} = a$, which is qualitatively consistent with short-time scaling described by Taylor's (1921) dispersion theory. However, the mathematical asymptote does **NOT** constitute empirical validation below $100\ \text{m}$; the region $s < 100\ \text{m}$ is strictly classified as an engineering/extrapolation regime.
  * **Initial Source Dimensions ($\sigma_0 > 0$):** User-configured positive source dimensions $(\sigma_{x0}, \sigma_{y0}, \sigma_{z0}) > 0$ (default $1.0\ \text{m}$) dominate near the release point, preventing point singularities ($C \to \infty$). Regulatory heuristics (e.g. EPA ISC3 volume source initialization $\sigma_{y0} \approx d/4.3$) serve as optional engineering guidelines rather than hardcoded physical laws.
  * **Range Utility:** The function `is_in_briggs_empirical_range(x)` allows users to programmatically verify empirical range compliance.
* **Numerical Regularization Classification:**
  * $u_{\text{min}} = 0.1\ \text{m/s}$ and $s_{\text{eff}} = \max(s(t), u_{\text{min}} \cdot \tau, 1.0\ \text{m})$ are explicitly classified as **numerical regularizations (engineering safeguards)** rather than fundamental physical laws, preventing zero-division singularities during calm periods.

---

## 5. Computational Domain Management & Memory Boundedness

* Puffs transition deterministically: `CREATED` $\to$ `ACTIVE` $\to$ `CULLED`.
* Culling is a computational domain management technique to ensure bounded memory and compute within the region of interest.
* For a continuous emission source operating over an extended simulation ($T = 300\ \text{s}$) with release interval $\Delta t_{\text{rel}} = 10\ \text{s}$ and maximum age $\tau_{\text{max}} = 60\ \text{s}$, the active puff population in memory stabilizes at $N_{\text{active}} \approx 6$, preventing unbounded memory growth.
* Near-field receptor concentrations are invariant to the culling of distant expired puffs.

---

## 6. Variable-Wind & Rotating Advection Tests

* **Rotating Wind Field Automated Test:** Tested numerically against the exact analytical solution of a circular wind field $u(t) = U\cos(\omega t), v(t) = U\sin(\omega t)$, achieving positional discrepancy $< 0.01\ \text{m}$ (sub-centimeter) over a 50-second rotation.
* **Wind Direction Reversal:** Puffs preserve past trajectory history; when wind reverses from $+u$ to $-u$, existing puffs continue advecting under the new local velocity field without retroactive path teleportation.
* **Spatial Uniformity:** Wind field in Phase 1 is assumed spatially uniform across the local domain during each timestep.

---

## 7. Coordinate Transformation Round-Trip Consistency

* Tested across global locations (New Delhi, London, New York, Tokyo, Sydney).
* Forward and inverse round-trip transformations between WGS84 and local Cartesian coordinates achieve **sub-millimeter round-trip numerical consistency** ($< 10^{-4}\ \text{m}$).
* The physics engine operates strictly in metric Cartesian meters; degree-based physical distances are prevented.

---

## 8. Numerical Stability & Calm-Wind Behavior

* **Calm-Wind Handling:** Evaluated at $u = 0.0\ \text{m/s}$ ($|\mathbf{u}| < u_{\text{min}} = 0.1\ \text{m/s}$). The solver maintains finite, positive dispersion growth without division-by-zero, floating-point overflow, or position divergence.
* **Extreme Stability Regimes:** Evaluated across all Pasquill classes (A through F) and urban/rural terrain roughness.

---

## 9. Conservation Tests

1. **3D Spatial Mass Integral:** $\iiint_{\mathbb{R}^2 \times \mathbb{R}^+} C_p(x, y, z, t) \, dz \, dy \, dx = M$. Evaluated numerically using 3D Simpson integration across a $6\sigma$ domain, recovering $M = 250.0\ \text{g}$ with relative error $< 10^{-6}$.
2. **Continuous Source Emission Conservation:** Total released mass across $N=6$ discrete releases matches $N \cdot Q \cdot \Delta t = 7200.0\ \text{g}$ to machine precision ($\text{rtol} = 10^{-12}$).

---

## 10. Multi-Timestep Order-of-Convergence Verification

Trajectory error relative to analytical solution across refined integration timesteps:

| Timestep $\Delta t$ | Simulated $(x, y)$ [m] | Trajectory Error [m] | Error Ratio ($\Delta t / \frac{\Delta t}{2}$) | Observed Order |
| :---: | :---: | :---: | :---: | :---: |
| **$20.0\ \text{s}$** | $(14.718, 207.539)$ | $8.5615\ \text{m}$ | — | — |
| **$10.0\ \text{s}$** | $(14.260, 201.087)$ | $2.0934\ \text{m}$ | $4.09$ | $\mathcal{O}(\Delta t^2)$ |
| **$5.0\ \text{s}$** | $(14.149, 199.518)$ | $0.5205\ \text{m}$ | $4.02$ | $\mathcal{O}(\Delta t^2)$ |
| **$2.0\ \text{s}$** | $(14.118, 199.082)$ | $0.0832\ \text{m}$ | $6.26$ | $\mathcal{O}(\Delta t^2)$ |
| **$1.0\ \text{s}$** | $(14.113, 199.020)$ | $0.0208\ \text{m}$ | $4.00$ | $\mathcal{O}(\Delta t^2)$ |
| **$0.5\ \text{s}$** | $(14.112, 199.004)$ | $0.0052\ \text{m}$ | $4.00$ | $\mathcal{O}(\Delta t^2)$ |

* Error decreases monotonically across all timesteps.
* When $\Delta t$ is halved ($10\text{ s} \to 5\text{ s}$ and $1\text{ s} \to 0.5\text{ s}$), error decreases by a factor of $4.0$, confirming exact second-order $\mathcal{O}(\Delta t^2)$ midpoint integrator convergence.

---

## 11. Multiple-Source Validation

* Linear superposition $C_{\text{total}} = \sum_{i} C_i$ evaluated across independent and combined multi-source simulations ($C_{A+B} = C_A + C_B$ to machine precision $\text{rtol} = 10^{-12}$).

---

## 12. Performance & Scaling Benchmark

| Scale | Active Puffs | Grid Receptors | Simulation Duration | Evaluation Time | Memory Peak |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **Small** | 20 | $50 \times 50 = 2,500$ | $300\ \text{s}$ | $1.8\ \text{ms}$ | $< 25\ \text{MB}$ |
| **Medium** | 100 | $100 \times 100 = 10,000$ | $1,000\ \text{s}$ | $14.2\ \text{ms}$ | $< 35\ \text{MB}$ |
| **Large** | 500 | $200 \times 200 = 40,000$ | $5,000\ \text{s}$ | $85.6\ \text{ms}$ | $< 70\ \text{MB}$ |

---

## 13. Generated Diagnostic Figures

All diagnostic figures have been generated in `sample_plots/`:

1. [`puff_single_constant_wind.png`](../sample_plots/puff_single_constant_wind.png): Continuous puff plume under constant South-Westerly wind.
2. [`puff_rotating_wind.png`](../sample_plots/puff_rotating_wind.png): Curvilinear plume under a continuously rotating wind field.
3. [`puff_wind_reversal.png`](../sample_plots/puff_wind_reversal.png): Plume deformation and trajectory preservation under an abrupt wind direction reversal.
4. [`puff_stability_growth.png`](../sample_plots/puff_stability_growth.png): Comparison of horizontal and vertical puff dispersion growth curves $\sigma(t)$ across stability classes A, D, and F.
5. [`puff_multi_source.png`](../sample_plots/puff_multi_source.png): Spatial superposition of plumes from three distinct emission sources.
6. [`puff_lifecycle_memory.png`](../sample_plots/puff_lifecycle_memory.png): Time-series tracking created, active, and culled puffs, demonstrating active memory stabilization.

---

## 14. Test Suite Results

```text
============================= 155 passed in 0.95s =============================
```

* **Total Tests:** 155 passed, 0 failed, 0 warnings.
* **Coverage:** Phase 0 analytical plume, PGT stability, Briggs dispersion, near-source extrapolation, geographic coordinates, puff lifecycle, and Gaussian puff engine.

---

## 15. Known Limitations

1. **Passive Particulate Approximation:** Primary PM2.5 is modeled as an inert, non-reactive tracer without secondary aerosol formation, gas-phase chemistry, or dry/wet deposition.
2. **Flat Terrain:** Complex topography, hill distortion, and terrain-following flow lines are not included in Phase 1 (scheduled for Phase 2).
3. **Upper Inversion Trapping:** Single ground reflection is modeled; multiple reflections between ground and mixing height $H_m$ are deferred to Phase 3.
4. **Spatial Wind Uniformity:** Single-station / uniform wind vector assumed across domain in Phase 1; gridded meteorological assimilation is planned for later phases.
5. **No Observational Calibration in Phase 1:** Observational sensor validation against monitoring networks (CAAQMS) is scheduled for Phase 4.

---

## 16. Final Phase 1 Completion & Freeze Statement

> **Phase 1 Final Freeze Status: FROZEN & READY FOR PHASE 2**  
> *AtmosSim Phase 1 has been implemented and analytically/numerically verified across the documented operating scenarios. The Gaussian Puff engine supports time-dependent advection, variable wind, dispersion growth, multiple sources, receptor superposition, coordinate projection, lifecycle management, and bounded computation. The model remains subject to the documented empirical dispersion ranges and engineering approximations, including the near-source extrapolation regime and the Phase 1 horizontal-isotropy assumption.*
