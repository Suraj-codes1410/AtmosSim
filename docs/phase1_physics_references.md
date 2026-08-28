# AtmosSim — Phase 1 Physics References & Gaussian Puff Foundation

## 1. Scope & Purpose

This document establishes the literature-grounded physical and mathematical foundation for the **Time-Dependent Gaussian Puff Engine** in **AtmosSim Phase 1**.

While Phase 0 established the steady-state Gaussian Plume analytical baseline for stationary advection, Phase 1 extends the modeling framework to **time-dependent, multi-puff Lagrangian dispersion** capable of simulating:
1. Non-stationary and time-varying horizontal wind vectors $\mathbf{U}(t) = (u(t), v(t))$,
2. Curvilinear trajectories, rotating wind fields, and wind direction reversals,
3. Multi-source release schedules with discrete mass creation $\Delta M = Q(t) \Delta t_{\text{rel}}$,
4. Dynamic dispersion growth $\sigma_x(t), \sigma_y(t), \sigma_z(t)$ based on cumulative Lagrangian travel distance and atmospheric stability,
5. Automated puff lifecycle management and computational domain memory boundedness,
6. Conformal geographic WGS84 to local metric Cartesian coordinate transformations.

---

## 2. Evidence Level Framework

AtmosSim strictly adheres to the standardized 5-tier evidence hierarchy established in Phase 0:

| Level | Designation | Definition | Phase 1 Status |
| :---: | :--- | :--- | :---: |
| **Level 1** | **Implemented** | Vectorized Python code is written, importable, modular, and executes deterministically. | **ACHIEVED** |
| **Level 2** | **Unit Tested** | Comprehensive test suite passes input validation, wind conversions, lifecycle culling, rotating winds, and multi-timestep convergence. | **ACHIEVED** |
| **Level 3** | **Analytically Verified** | Code reproduces exact closed-form 3D Gaussian integrals, constant/variable/rotating wind trajectories, and linear superposition. | **ACHIEVED** |
| **Level 4** | **Literature Reproduced** | Formulations and parameters directly follow published EPA and atmospheric modeling guidance. | **ACHIEVED** (Equation Provenance) |
| **Level 5** | **Observationally Validated** | Model evaluated against physical ground monitoring observations (e.g. CAAQMS). | **DEFERRED (Phase 4)** |

---

## 3. Gaussian Puff Governing Equation

### 3.1 3D Spatial Formulation
For an individual Lagrangian puff parcel $p$ containing pollutant mass $M(t)$ with center coordinates $\mathbf{x}_p(t) = (x_p(t), y_p(t), z_p(t))$ and spatial standard deviations $\sigma_x(t), \sigma_y(t), \sigma_z(t)$, the instantaneous 3D concentration field $C_p(x, y, z, t)$ in an unbounded domain is:

$$
C_p(x, y, z, t) = \frac{M(t)}{(2\pi)^{3/2} \sigma_x(t) \sigma_y(t) \sigma_z(t)} \exp\left( -\frac{(x - x_p(t))^2}{2\sigma_x^2(t)} - \frac{(y - y_p(t))^2}{2\sigma_y^2(t)} - \frac{(z - z_p(t))^2}{2\sigma_z^2(t)} \right)
$$

### 3.2 Method-of-Images Ground Reflection
Under the assumption of an impermeable ground surface ($z=0$) with zero dry deposition flux ($\partial C / \partial z = 0$ at $z=0$), an identical image source is positioned at $(x_p, y_p, -z_p)$:

$$
C_p(x, y, z, t) = \frac{M(t)}{(2\pi)^{3/2} \sigma_x \sigma_y \sigma_z} \exp\left( -\frac{(x - x_p)^2}{2\sigma_x^2} - \frac{(y - y_p)^2}{2\sigma_y^2} \right) \left[ \exp\left( -\frac{(z - z_p)^2}{2\sigma_z^2} \right) + \exp\left( -\frac{(z + z_p)^2}{2\sigma_z^2} \right) \right]
$$

At ground level ($z=0$), the vertical term evaluates to $2 \exp(-z_p^2 / (2\sigma_z^2))$, doubling the concentration compared to an unconfined domain.

---

## 4. Puff Mass & Continuous Source Discretization

### 4.1 Discrete Mass Creation
A continuous emission source releasing pollutant mass at rate $Q(t)\ [\text{g/s}]$ is discretized into a temporal series of puff parcels emitted at regular intervals $\Delta t_{\text{rel}}\ [\text{s}]$. The initial mass $\Delta M$ assigned to a newly generated puff parcel is:

$$
\Delta M = Q(t) \cdot \Delta t_{\text{rel}}\quad [\text{g}]
$$

### 4.2 Cumulative Mass Conservation
For a source operating over total duration $T = N \cdot \Delta t_{\text{rel}}$ with constant emission rate $Q$, the total released mass is:

$$
M_{\text{total}} = \sum_{k=1}^{N} \Delta M_k = N \cdot (Q \cdot \Delta t_{\text{rel}}) = Q \cdot T\quad [\text{g}]
$$

---

## 5. Longitudinal Dispersion ($\sigma_x$) Provenance & Qualifications

### 5.1 Literature Justification for Horizontal Isotropy ($\sigma_x = \sigma_y$)
In steady-state plume modeling, longitudinal turbulent diffusion is neglected because mean advective transport $u \frac{\partial C}{\partial x}$ dominates along-wind spread. For a Lagrangian puff parcel, turbulent expansion occurs in all spatial directions.

The equality $\sigma_x(t) = \sigma_y(t)$ is established on the following theoretical and regulatory foundation:
1. **Statistical Turbulence Theory (Taylor, 1921; Batchelor, 1950, 1952):** In boundary-layer turbulence without strong directional shear, horizontal turbulent eddy diffusivities in the along-wind ($x$) and crosswind ($y$) directions are approximately isotropic on the meso-beta and local scales ($K_x \approx K_y$).
2. **Turbulent Diffusion Schemes (Gifford, 1976):** Reviews of instantaneous puff diffusion data demonstrate that horizontal puff growth exhibits circular symmetry in the horizontal plane during early and intermediate travel times.
3. **Regulatory Puff Modeling Conventions (CALPUFF, Scire et al., 2000, Section 2.1.2; Zannetti, 1990, Chapter 6):** Standard regulatory Gaussian puff models (e.g. CALPUFF, MESOPUFF II, INPUFF 2.0) set:
   $$\sigma_x(t) = \sigma_y(t)$$

### 5.2 Physical Qualifications & Limitations of $\sigma_x = \sigma_y$
* **Isotropy Assumption:** $\sigma_x = \sigma_y$ is an engineering approximation valid when horizontal turbulent eddies are isotropic.
* **Vertical Wind Shear Limitation:** In environments with strong vertical wind shear (speed and direction changes with height), differential vertical advection stretches puffs along the longitudinal axis into elongated ellipses ($\sigma_x > \sigma_y$). This shear-stretching effect is not modeled by isotropic Gaussian puffs in Phase 1.

---

## 6. Cumulative Travel Distance & Briggs Parameterization Defensibility

### 6.1 Equivalent Travel Distance / Virtual Distance Method
In time-varying wind fields, a puff's travel speed and trajectory change over time. To compute dispersion growth $\sigma_y(t)$ and $\sigma_z(t)$, AtmosSim employs the **equivalent travel distance / virtual distance method** (Ludwig et al., 1977; Zannetti, 1990; Scire et al., 2000):

The cumulative Lagrangian path length $s(t)$ integrated along the puff trajectory is:

$$
s(t) = \int_{t_{\text{rel}}}^t |\mathbf{U}(t')| \, dt' \approx \sum_{k} |\mathbf{U}_k| \, \Delta t_k
$$

The empirical Briggs (1973) dispersion curves $\sigma_y^{\text{Briggs}}(x), \sigma_z^{\text{Briggs}}(x)$ verified in Phase 0 are evaluated at downwind distance $x = s_{\text{eff}}$:

$$
\sigma_y(s) = \sqrt{\sigma_{y0}^2 + [\sigma_y^{\text{Briggs}}(s_{\text{eff}})]^2}, \quad \sigma_x(s) = \sigma_y(s), \quad \sigma_z(s) = \sqrt{\sigma_{z0}^2 + [\sigma_z^{\text{Briggs}}(s_{\text{eff}})]^2}
$$

where $\sigma_{x0}, \sigma_{y0}, \sigma_{z0} > 0$ are initial finite source dimensions (default $1.0\ \text{m}$), eliminating point singularities at release ($\tau=0$).

### 6.2 Inherited Briggs Empirical Validity Limits & Near-Source Region ($s < 100\ \text{m}$) Audit
* **Distance Regime Classification:**
  1. **$0 < s < 100\ \text{m}$ (Near-Source Engineering / Extrapolation Regime):** Below the documented empirical calibration range. Governed primarily by initial source dimensions and engineering defaults; mathematical asymptote applies.
  2. **$100\ \text{m} \le s \le 10,000\ \text{m}$ (Briggs Empirical Core):** Calibrated from field tracer campaigns (Prairie Grass, Round Hill, Porton Down).
  3. **$s > 10,000\ \text{m}$ (Far-Field Extrapolation Regime):** Outside documented empirical calibration range; subject to regional dispersion uncertainty.
* **Mathematical Asymptote vs. Physical Theory:**
  * The selected Briggs parameterizations possess a mathematically linear asymptotic form as $s \to 0^+$ ($\lim_{s \to 0^+} \frac{\sigma(s)}{s} = a$).
  * This behavior is **qualitatively consistent** with the short-time scaling described by Taylor's (1921) dispersion theory ($\sigma \propto \sigma_v \cdot t$).
  * However, the Briggs coefficients are empirically calibrated over a finite range ($100\ \text{m} \le s \le 10,000\ \text{m}$), and the mathematical asymptote does **NOT** constitute empirical validation outside that range. AtmosSim therefore treats the region below the documented 100 m empirical range as a near-source engineering/extrapolation regime.
* **Initial Source Dimensions ($\sigma_0 > 0$):**
  * In the Gaussian Puff formulation, total dispersion is $\sigma_{\text{total}}(s) = \sqrt{\sigma_0^2 + [\sigma^{\text{Briggs}}(s_{\text{eff}})]^2}$.
  * At early puff ages ($s \to 0$), the user-configured finite source dimensions $(\sigma_{x0}, \sigma_{y0}, \sigma_{z0}) > 0$ (default $1.0\ \text{m}$) dominate the total spread, preventing point singularities ($C \to \infty$) at release.
  * *Heuristic Reference:* Regulatory models (e.g. EPA ISC3 / AERMOD) employ an initialization heuristic for volume sources where $\sigma_{y0} \approx d / 4.3$ (assuming source diameter spans $4.3 \sigma \approx \pm 2.15 \sigma$). AtmosSim does not hard-code this heuristic into the solver, but provides explicit user-configurable $\sigma_{x0}, \sigma_{y0}, \sigma_{z0}$ parameters and enforces strict positivity ($\sigma_0 > 0$).
* **Range Utility:** The function `is_in_briggs_empirical_range(x)` in `atmosim.physics.dispersion` programmatically flags whether evaluations fall within the empirical core $[100, 10000]\ \text{m}$ or within the near-source / far-field extrapolation zones.

---

## 7. Numerical Regularization for Calm Winds ($u_{\text{min}}$ and $s_{\text{eff}}$)

### 7.1 Explicit Classification as Numerical Regularization
> [!IMPORTANT]
> The parameters $u_{\text{min}} = 0.1\ \text{m/s}$ and $s_{\text{eff}} = \max(s(t), u_{\text{min}} \cdot \tau, 1.0\ \text{m})$ are **NUMERICAL REGULARIZATIONS (engineering safeguards)**, NOT fundamental physical laws.

### 7.2 Rationale & Numerical Function
* Under stagnant calm conditions ($|\mathbf{U}| \to 0$), exact advective distance $s(t) \to 0$. Evaluating dispersion formulas at $s=0$ would freeze puff expansion or cause division-by-zero in analytical formulations.
* In real atmospheres, non-zero turbulent diffusion persists even when mean advective wind vanishes ($u \approx 0$).
* Setting $s_{\text{eff}} = \max(s(t), u_{\text{min}} \cdot \tau, 1.0\ \text{m})$ regularizes the solver, preventing zero-division singularities and numerical freeze while ensuring smooth, continuous, non-zero Gaussian spread.

---

## 8. Lagrangian Advection & Spatial Wind Uniformity Assumption

### 8.1 Second-Order Trajectory Integration
The puff center position $\mathbf{x}_p(t) = (x_p(t), y_p(t), z_p(t))$ is integrated using second-order midpoint velocity integration:

$$
\mathbf{x}_p(t + \Delta t) = \mathbf{x}_p(t) + \mathbf{U}\left( \mathbf{x}_p(t) + \frac{1}{2}\mathbf{U}(\mathbf{x}_p, t)\Delta t, t + \frac{1}{2}\Delta t \right) \Delta t
$$

### 8.2 Spatial Uniformity Assumption in Phase 1
In Phase 1, the horizontal wind velocity field $\mathbf{U}(t) = (u(t), v(t))$ is assumed to be **spatially uniform across the local computational domain** during each timestep. Spatially gridded, non-uniform meteorological wind fields and terrain-following flow lines are introduced in later phases.

### 8.3 Path History Preservation
Each puff retains its individual historical spatial trajectory. When the regional wind vector changes direction (e.g., from Eastward to Westward), existing puffs continue advecting according to the new velocity field without retroactive teleportation or past path alteration.

---

## 9. Wind Direction Conventions & Meteorological Conversions

Meteorological wind direction $\theta_{\text{met}}$ defines the direction **FROM** which the wind originates, measured clockwise from True North:
* North wind: $\theta_{\text{met}} = 0^\circ$ (blows toward South, $+y \to -y$)
* East wind: $\theta_{\text{met}} = 90^\circ$ (blows toward West, $+x \to -x$)
* South wind: $\theta_{\text{met}} = 180^\circ$ (blows toward North, $-y \to +y$)
* West wind: $\theta_{\text{met}} = 270^\circ$ (blows toward East, $-x \to +x$)

Conversion to Cartesian velocity components $(u, v)$ in local metric coordinates ($+x=\text{East}, +y=\text{North}$):

$$
u = -U \sin\left(\frac{\pi \theta_{\text{met}}}{180^\circ}\right), \quad v = -U \cos\left(\frac{\pi \theta_{\text{met}}}{180^\circ}\right)
$$

Reverse conversion from Cartesian velocity $(u, v)$ to meteorological $(U, \theta_{\text{met}})$:

$$
U = \sqrt{u^2 + v^2}, \quad \theta_{\text{met}} = \left( 270^\circ - \text{atan2}(v, u) \cdot \frac{180^\circ}{\pi} \right) \pmod{360^\circ}
$$

---

## 10. Computational Domain Management & Puff Culling

### 10.1 Computational vs Physical Semantics
> [!NOTE]
> Puff culling in AtmosSim is a **COMPUTATIONAL DOMAIN MANAGEMENT TECHNIQUE** designed to keep active memory footprint and evaluation runtime strictly bounded. It does not represent physical particle loss (which is modeled separately via exponential decay or dry deposition).

### 10.2 Configurable Culling Policies (`PuffLifecycleConfig`)
1. **Maximum Age:** Culled when age $\tau = t - t_{\text{rel}} > \tau_{\text{max}}$ (default $7200\ \text{s} = 2\ \text{hours}$).
2. **Maximum Distance:** Culled when radial distance from source $\sqrt{(x-x_s)^2 + (y-y_s)^2} > r_{\text{max}}$ (default $50,000\ \text{m}$).
3. **Minimum Mass:** Culled if pollutant mass $M < M_{\text{min}}$ (default $10^{-8}\ \text{g}$).
4. **Domain Bounding Box:** Culled when leaving configured 3D computational boundaries $[x_{\text{min}}, x_{\text{max}}] \times [y_{\text{min}}, y_{\text{max}}] \times [z_{\text{min}}, z_{\text{max}}]$.

**Memory Boundedness Property:** For continuous emissions with release interval $\Delta t_{\text{rel}}$ and maximum lifetime $\tau_{\text{max}}$, the active puff population in memory is strictly bounded by $N_{\text{active}} \approx \tau_{\text{max}} / \Delta t_{\text{rel}}$, preventing unbounded memory growth.

---

## 11. Geographic Coordinate Projections

* **Geodetic Datum:** WGS84 (`EPSG:4326`).
* **Projected System:** Universal Transverse Mercator (UTM) or Local Conformal Projection centered on $(\text{lat}_0, \text{lon}_0)$.
* **Implementation:** [`src/atmosim/physics/coordinates.py`](../src/atmosim/physics/coordinates.py) using `pyproj`.
* **Numerical Consistency:** Forward and reverse round-trip geodetic transformations achieve sub-millimeter round-trip numerical consistency ($< 10^{-4}\ \text{m}$).
* **Rule:** The physics engine operates exclusively in metric Cartesian meters; degree-based physical distances are prevented.

---

## 12. Proof of 3D Spatial Mass Conservation

For a single conservative puff with mass $M$ at $(x_p, y_p, z_p)$ with method-of-images reflection:

$$
\int_{-\infty}^{\infty} \int_{-\infty}^{\infty} \int_{0}^{\infty} C_p(x, y, z, t) \, dz \, dy \, dx = M
$$

1. $\int_{-\infty}^{\infty} \exp\left(-\frac{(x-x_p)^2}{2\sigma_x^2}\right) dx = \sqrt{2\pi}\sigma_x$
2. $\int_{-\infty}^{\infty} \exp\left(-\frac{(y-y_p)^2}{2\sigma_y^2}\right) dy = \sqrt{2\pi}\sigma_y$
3. $\int_{0}^{\infty} \left[ \exp\left(-\frac{(z-z_p)^2}{2\sigma_z^2}\right) + \exp\left(-\frac{(z+z_p)^2}{2\sigma_z^2}\right) \right] dz = \sqrt{2\pi}\sigma_z$

Multiplying by the prefactor:

$$
\frac{M}{(2\pi)^{3/2} \sigma_x \sigma_y \sigma_z} \cdot (\sqrt{2\pi}\sigma_x) \cdot (\sqrt{2\pi}\sigma_y) \cdot (\sqrt{2\pi}\sigma_z) = M
$$

This exact mass conservation invariant is verified numerically in [`tests/test_puff.py`](../tests/test_puff.py) using 3D Simpson quadrature (`test_puff_mass_conservation_3d_integral`), recovering $M = 250.0\ \text{g}$ with relative error $< 10^{-6}$.

---

## 13. Equation Provenance Table

| Component | Selected Formulation | Primary Authoritative Source | Section / Equation | Evidence Level |
| :--- | :--- | :--- | :--- | :---: |
| **Gaussian Puff** | 3D Gaussian with method-of-images reflection | Turner (1970) AP-26; Seinfeld & Pandis (2016) | AP-26 Chap. 5; Eq. 18.52–18.58 | Level 3 |
| **Longitudinal Dispersion $\sigma_x$** | Horizontal isotropy ($\sigma_x = \sigma_y$) | Taylor (1921); Gifford (1976); Scire et al. (2000) | CALPUFF User's Guide Sec. 2.1.2 | Level 3 |
| **Travel Distance Growth** | Cumulative path length $s(t) = \int |\mathbf{u}| dt$ | Ludwig et al. (1977); Zannetti (1990) | Atmos. Environ. 11(5); Chap. 6 | Level 3 |
| **Puff Mass Release** | $\Delta M = Q(t) \Delta t_{\text{rel}}$ | Zannetti (1990); Scire et al. (2000) | Air Pollution Modeling Chap. 6 | Level 3 |
| **Wind Conversion** | Meteorological from-bearing to Cartesian $(u, v)$ | Standard Atmospheric Science Convention | AMS Glossary of Meteorology | Level 3 |
| **Coordinate Projection** | WGS84 to local UTM via `pyproj` | Snyder (1987) USGS Paper 1395 | DMA Technical Manual 8358.2 | Level 2 |
| **Calm Regularization** | $s_{\text{eff}} = \max(s, u_{\text{min}}\tau, 1.0)$ | Engineering Regularization Safeguard | Numerical Guard | Level 2 |
| **Puff Lifecycle** | Multi-criteria computational domain culling | Scire et al. (2000) CALPUFF | CALPUFF Sec. 2.1 | Level 2 |

---

## 14. Scope & Known Limitations

1. **Passive Particulate Approximation:** Primary PM2.5 is treated as an inert, non-reactive tracer without secondary aerosol chemistry, gas-to-particle conversion, or dry/wet deposition in Phase 1.
2. **Flat Terrain:** Complex topography and terrain-following flow lines are deferred to Phase 2.
3. **Upper Boundary Inversion:** Plumes expand into a semi-infinite half-space $z \ge 0$; multiple boundary-layer reflections at mixing height $z = H_m$ are planned for Phase 3.
4. **Spatial Wind Uniformity:** Single-station / uniform wind vector assumed across domain in Phase 1; gridded meteorological assimilation is planned for later phases.
5. **Observational Validation:** Real-world sensor comparison is explicitly scheduled for Phase 4.

---

## 15. Authoritative Literature References

1. **Batchelor, G. K. (1950).** *The application of the similarity theory of turbulence to atmospheric diffusion.* Quarterly Journal of the Royal Meteorological Society, 76(328), 133–146.
2. **Batchelor, G. K. (1952).** *Diffusion in a field of homogeneous turbulence: II. The relative motion of particles.* Proceedings of the Cambridge Philosophical Society, 48(2), 345–362.
3. **Briggs, G. A. (1973).** *Diffusion Estimation for Small Emissions.* ATDL Report No. 79, Atmospheric Turbulence and Diffusion Laboratory, NOAA/ARL, Oak Ridge, TN.
4. **Gifford, F. A. (1976).** *Turbulent diffusion-typing schemes: A review.* Nuclear Safety, 17(1), 68–86.
5. **Ludwig, F. L., Gasiorek, L. S., & Ruff, R. E. (1977).** *Simplification of a Gaussian puff model for real-time minicomputer use.* Atmospheric Environment, 11(5), 431–436.
6. **Scire, J. S., Strimaitis, D. G., & Yamartino, R. J. (2000).** *A User's Guide for the CALPUFF Dispersion Model.* Earth Tech, Inc., Concord, MA.
7. **Seinfeld, J. H., & Pandis, S. N. (2016).** *Atmospheric Chemistry and Physics: From Air Pollution to Climate Change* (3rd ed.). John Wiley & Sons, Hoboken, NJ. Chapter 18.
8. **Snyder, J. P. (1987).** *Map Projections—A Working Manual.* U.S. Geological Survey Professional Paper 1395, Washington, D.C.
9. **Taylor, G. I. (1921).** *Diffusion by continuous movements.* Proceedings of the London Mathematical Society, 2(1), 196–212.
10. **Turner, D. B. (1970).** *Workbook of Atmospheric Dispersion Estimates.* U.S. Environmental Protection Agency, Office of Air Programs Publication No. AP-26. Chapter 5.
11. **Zannetti, P. (1990).** *Air Pollution Modeling: Theories, Computational Methods and Available Software.* Computational Mechanics Publications / Van Nostrand Reinhold. Chapter 6.
