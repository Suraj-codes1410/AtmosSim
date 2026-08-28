# AtmosSim — Phase 0 Physics References & Scientific Foundation

## 1. Scope & Purpose

**AtmosSim** is an open-source, physics-to-machine-learning benchmark framework for atmospheric dispersion modeling.

The objective of **Phase 0** is to establish a **literature- and authoritative-guidance-grounded physical foundation** and an analytically verified steady-state baseline. This document details:
1. The governing analytical equations, Cartesian coordinate conventions, and strict SI unit policies.
2. The mathematical derivation of the steady-state Gaussian plume model with method-of-images ground reflection.
3. The Pasquill-Gifford-Turner (PGT) stability classification methodology.
4. The Briggs (1973, 1974) empirical dispersion coefficient parameterizations ($\sigma_y$, $\sigma_z$) for rural and urban surface regimes.
5. The Holzworth (1972) boundary-layer mixing height methodology and specification.
6. Rigorous mathematical proofs of mass flux conservation, numerical convergence, and analytical reference cases.
7. Explicit documentation of mathematical assumptions, scope boundaries, and known physical limitations.

---

## 2. Evidence Levels Framework

To prevent scientific overclaims, AtmosSim documents all physical modules using a five-tier evidence hierarchy:

| Level | Designation | Definition | Phase 0 Status |
| :---: | :--- | :--- | :---: |
| **Level 1** | **Implemented** | Python code is written, importable, vectorized, and executes deterministically. | **ACHIEVED** |
| **Level 2** | **Unit Tested** | Automated test suite passes comprehensive input boundary, invariant, and error tests. | **ACHIEVED** |
| **Level 3** | **Analytically Verified** | Code reproduces exact closed-form mathematical equations, symmetry invariants, scaling laws, and flux conservation integrals. | **ACHIEVED** |
| **Level 4** | **Literature Reproduced** | Code reproduces published worked numerical examples from literature references. | **PARTIALLY ACHIEVED** (Equation provenance verified; numerical cases are independently derived from literature equations) |
| **Level 5** | **Observationally Validated** | Model outputs have been statistically evaluated against real-world physical sensor observations. | **DEFERRED (Phase 4)** |

---

## 3. Coordinate System

AtmosSim defines a right-handed Cartesian coordinate system $(x, y, z)$ anchored to the ground surface:

```
           z (Vertical height above ground, z >= 0)
           ^
           |     +--- Plume Centerline (z = H, y = 0)
           |    /
           |   /
           |  /
           | /   
 (0,0,0)   +----------------------------> x (Downwind distance along mean wind vector, x > 0)
          /
         /
        /
       v
      y (Horizontal crosswind coordinate, y = 0 at centerline)
```

### Coordinate Definitions:
* **Origin $(0, 0, 0)$**: Defined at the surface (ground level, $z=0$) directly beneath the emission point source.
* **Downwind Axis ($x$)**: Oriented along the horizontal mean advection wind vector $\mathbf{u}$. Units: meters ($\text{m}$). Evaluated strictly for $x > 0$. Points $x \le 0$ represent upwind positions where steady-state advection implies zero advective concentration.
* **Crosswind Axis ($y$)**: Oriented perpendicular to the mean wind direction in the horizontal plane. Units: meters ($\text{m}$). $y = 0$ corresponds to the central advective plume axis. $y > 0$ denotes crosswind displacement to the left of the wind vector; $y < 0$ denotes displacement to the right.
* **Vertical Axis ($z$)**: Height above local ground level. Units: meters ($\text{m}$). Evaluated strictly for $z \ge 0$.
* **Source Location**: The effective point release occurs at $(0, 0, H)$, where $H$ is the effective release height in meters.

---

## 4. Strict Units Policy

AtmosSim enforces internal physical consistency using the International System of Units (SI):

| Symbol | Physical Quantity | Standard Internal Unit | Valid Domain / Constraint | Dimensionality |
| :--- | :--- | :--- | :--- | :--- |
| $Q$ | Mass emission rate | $\text{g/s}$ (or $\text{kg/s}$) | $Q \ge 0$, finite | $[M T^{-1}]$ |
| $u$ | Mean horizontal advective wind speed | $\text{m/s}$ | $u > 0$, finite | $[L T^{-1}]$ |
| $x$ | Downwind distance along plume axis | $\text{m}$ | $x > 0$, finite | $[L]$ |
| $y$ | Horizontal crosswind coordinate | $\text{m}$ | $-\infty < y < \infty$, finite | $[L]$ |
| $z$ | Receptor vertical height above ground | $\text{m}$ | $z \ge 0$, finite | $[L]$ |
| $H$ | Effective emission release height | $\text{m}$ | $H \ge 0$, finite | $[L]$ |
| $\sigma_y(x)$ | Horizontal crosswind dispersion standard deviation | $\text{m}$ | $\sigma_y > 0$, finite | $[L]$ |
| $\sigma_z(x)$ | Vertical dispersion standard deviation | $\text{m}$ | $\sigma_z > 0$, finite | $[L]$ |
| $C(x, y, z)$ | Mass concentration | $\text{g/m}^3$ (or $\text{kg/m}^3$, $\mu\text{g/m}^3$) | $C \ge 0$, finite | $[M L^{-3}]$ |
| $R_s$ | Solar downwelling irradiance | $\text{W/m}^2$ | $R_s \ge 0$, finite | $[M T^{-3}]$ |
| $\theta_{\text{elev}}$ | Solar elevation angle above horizon | $\text{degrees}\ (^\circ)$ | $0^\circ \le \theta_{\text{elev}} \le 90^\circ$ | Dimensionless |
| $f_{\text{cloud}}$ | Fractional cloud cover | Fraction $[0.0, 1.0]$ | $0.0 \le f_{\text{cloud}} \le 1.0$ | Dimensionless |
| $H_m$ | Planetary boundary layer mixing height | $\text{m}$ | $H_m > 0$, finite | $[L]$ |

### Conversion Invariants:
* Parameterizations originating with distance in kilometers (e.g. $x$ in $\text{km}$) are converted at the function boundary so that all API interfaces accept and return SI units ($\text{m}$, $\text{m/s}$, $\text{g/s}$).
* Concentration outputs directly inherit the mass numerator of $Q$: If $Q$ is supplied in $\text{g/s}$, $C$ is evaluated in $\text{g/m}^3$ ($1\ \text{g/m}^3 = 10^6\ \mu\text{g/m}^3$).

---

## 5. Gaussian Plume Governing Equation

### 5.1 Analytical Formulation
For a continuous point source emitting at $(0, 0, H)$ into a steady, horizontally homogeneous atmosphere with mean wind speed $u$, the steady-state 3D concentration field $C(x, y, z)$ with method-of-images ground reflection is:

$$
C(x, y, z) = \frac{Q}{2\pi u \sigma_y(x) \sigma_z(x)} \exp\left( -\frac{y^2}{2\sigma_y^2(x)} \right) \left[ \exp\left( -\frac{(z - H)^2}{2\sigma_z^2(x)} \right) + \exp\left( -\frac{(z + H)^2}{2\sigma_z^2(x)} \right) \right]
$$

### 5.2 Mathematical Derivation of Ground Reflection (Method of Images)
Under the idealized physical condition that the ground surface is an impermeable boundary with zero deposition flux, the vertical gradient at $z=0$ must vanish:

$$
\left. \frac{\partial C}{\partial z} \right|_{z=0} = 0
$$

To satisfy this Neumann boundary condition analytically, a virtual image source of identical emission strength $Q$ is placed at $(0, 0, -H)$ in the unbounded domain $z \in (-\infty, \infty)$:

$$
C(x, y, z) = \frac{Q}{2\pi u \sigma_y \sigma_z} \exp\left( -\frac{y^2}{2\sigma_y^2} \right) \left[ \exp\left( -\frac{(z - H)^2}{2\sigma_z^2} \right) + \exp\left( -\frac{(z + H)^2}{2\sigma_z^2} \right) \right]
$$

Differentiating with respect to $z$ at $z=0$:

$$
\left. \frac{\partial C}{\partial z} \right|_{z=0} \propto \left[ -\frac{(0 - H)}{\sigma_z^2} \exp\left( -\frac{H^2}{2\sigma_z^2} \right) - \frac{(0 + H)}{\sigma_z^2} \exp\left( -\frac{H^2}{2\sigma_z^2} \right) \right] = \frac{H}{\sigma_z^2} e^{-H^2/(2\sigma_z^2)} - \frac{H}{\sigma_z^2} e^{-H^2/(2\sigma_z^2)} = 0
$$

Thus, the zero-flux boundary condition is rigorously satisfied. At ground level ($z=0$), both exponential terms become identical ($\exp(-H^2/(2\sigma_z^2))$), doubling the concentration relative to an unconfined free plume:

$$
C(x, y, z=0) = \frac{Q}{\pi u \sigma_y(x) \sigma_z(x)} \exp\left( -\frac{y^2}{2\sigma_y^2(x)} \right) \exp\left( -\frac{H^2}{2\sigma_z^2(x)} \right)
$$

### 5.3 Assumptions & Scope Qualifications

#### Fluid-Dynamical & Mathematical Assumptions:
1. **Steady-State Continuity ($\partial C / \partial t = 0$):** Advective transport and turbulent diffusion are in exact stationary equilibrium.
2. **Advection Dominance ($u \ge 1\ \text{m/s}$):** Along-wind advection $u \frac{\partial C}{\partial x}$ dominates longitudinal diffusion $\frac{\partial}{\partial x}(K_x \frac{\partial C}{\partial x})$, allowing longitudinal dispersion to be neglected in the steady plume.
3. **Homogeneous Stationary Wind Field:** Mean wind vector $\mathbf{u} = (u, 0, 0)$ is constant over space and time.
4. **Gaussian Crosswind and Vertical Spread:** Displacements follow normal Gaussian distributions with spatial variances $\sigma_y^2(x)$ and $\sigma_z^2(x)$.
5. **Method-of-Images Ground Reflection:** Perfect reflection at the ground surface without dry deposition or chemical absorption.

#### Scope Qualifications for AtmosSim:
* **Primary PM2.5 / Passive Particulate Tracer Approximation:** Phase 0 treats emitted particulate matter as a passive, non-reactive tracer without secondary aerosol formation, gas-to-particle partitioning, chemical reactions, or gravitational settling.
* **No Complex Terrain:** Surface topography is assumed flat and uniform.
* **Longitudinal Dispersion ($\sigma_x$) Reserved for Phase 1:** Phase 0 covers steady-state lateral ($\sigma_y$) and vertical ($\sigma_z$) plume dispersion. Longitudinal dispersion $\sigma_x$ applies to transient Gaussian Puffs and will undergo independent literature verification in Phase 1.

---

## 6. Atmospheric Stability Classification

Atmospheric stability governs turbulent kinetic energy and vertical convective motions. AtmosSim implements the Pasquill-Gifford-Turner (PGT) framework (Pasquill, 1961; Turner, 1964; EPA ISC3, 1995).

### 6.1 Stability Classes (A through F)

| Class | Description | Physical Turbulence Characteristics |
| :---: | :--- | :--- |
| **A** | Extremely Unstable | Intense solar heating, low wind speeds, strong convective updrafts |
| **B** | Moderately Unstable | Moderate solar heating, buoyant and mechanical mixing |
| **C** | Slightly Unstable | Weak solar heating or moderate wind speeds |
| **D** | Neutral | Overcast skies, high winds ($u \ge 6\ \text{m/s}$), or transition periods; near-adiabatic lapse rate |
| **E** | Slightly Stable | Nighttime with moderate cloudiness, weak positive thermal gradient |
| **F** | Moderately/Extremely Stable | Clear nighttime, light winds ($u < 3\ \text{m/s}$), strong surface temperature inversion |

### 6.2 Solar Insolation & Cloud Cover Criteria

* **Strong Insolation:** Downwelling solar irradiance $R_s > 600\ \text{W/m}^2$ or solar elevation angle $\theta_{\text{elev}} > 60^\circ$ (Turner, 1964; EPA SRDT, 1999).
* **Moderate Insolation:** $300\ \text{W/m}^2 \le R_s \le 600\ \text{W/m}^2$ or $35^\circ \le \theta_{\text{elev}} \le 60^\circ$.
* **Slight Insolation:** $0 < R_s < 300\ \text{W/m}^2$ or $15^\circ \le \theta_{\text{elev}} < 35^\circ$.
* **Nighttime Cloud Cover:**
  * Cloudy Night: Fractional cloud cover $f_{\text{cloud}} \ge 0.5$ ($\ge 4/8$ octas).
  * Clear Night: Fractional cloud cover $f_{\text{cloud}} < 0.5$ ($< 4/8$ octas).
  * Overcast Invariant: $f_{\text{cloud}} \ge 0.875$ ($\ge 7/8$ octas) is assigned to **Class D (Neutral)** regardless of wind speed, day, or night.

### 6.3 PGT Decision Table (Pasquill, 1961; Turner, 1964)

| 10m Wind Speed $u$ | Daytime: Strong ($>600\ \text{W/m}^2$) | Daytime: Moderate ($300-600\ \text{W/m}^2$) | Daytime: Slight ($<300\ \text{W/m}^2$) | Night: Cloudy ($\ge 4/8$) | Night: Clear ($< 4/8$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| $u < 2\ \text{m/s}$ | **A** | **B** | **B** | **E** | **F** |
| $2 \le u < 3\ \text{m/s}$ | **A** | **B** | **C** | **E** | **F** |
| $3 \le u < 5\ \text{m/s}$ | **B** | **C** | **C** | **D** | **E** |
| $5 \le u < 6\ \text{m/s}$ | **C** | **C** | **D** | **D** | **D** |
| $u \ge 6\ \text{m/s}$ | **C** | **D** | **D** | **D** | **D** |

---

## 7. Briggs (1973, 1974) Dispersion Parameterizations

Dispersion coefficients represent the standard deviations $\sigma_y(x)$ and $\sigma_z(x)$ of the Gaussian concentration profile. AtmosSim implements the continuous mathematical formulations developed by **Briggs (1973)** at the NOAA Atmospheric Turbulence and Diffusion Laboratory (ATDL Report No. 79).

* **Input:** $x$ downwind distance in meters ($\text{m}$).
* **Output:** $\sigma_y, \sigma_z$ in meters ($\text{m}$).
* **Empirical Range:** $100\ \text{m} \le x \le 10,000\ \text{m}$ ($0.1\ \text{km} \le x \le 10\ \text{km}$).

### 7.1 Rural Parameterizations (Briggs, 1973, Table 1)
$$\sigma_y(x) = \frac{a_y \cdot x}{\sqrt{1 + 0.0001 \cdot x}}$$

| Class | $a_y$ | Vertical Dispersion $\sigma_z(x)\ [\text{m}]$ |
| :---: | :---: | :--- |
| **A** | 0.22 | $\sigma_z = 0.20 \cdot x$ |
| **B** | 0.16 | $\sigma_z = 0.12 \cdot x$ |
| **C** | 0.11 | $\sigma_z = \frac{0.08 \cdot x}{\sqrt{1 + 0.0002 \cdot x}}$ |
| **D** | 0.08 | $\sigma_z = \frac{0.06 \cdot x}{\sqrt{1 + 0.0015 \cdot x}}$ |
| **E** | 0.06 | $\sigma_z = \frac{0.03 \cdot x}{1 + 0.0003 \cdot x}$ |
| **F** | 0.04 | $\sigma_z = \frac{0.016 \cdot x}{1 + 0.0003 \cdot x}$ |

### 7.2 Urban Parameterizations (Briggs, 1973 / McElroy-Pooler, 1968)
$$\sigma_y(x) = \frac{a_y \cdot x}{\sqrt{1 + 0.0004 \cdot x}}$$

| Class | $a_y$ | Vertical Dispersion $\sigma_z(x)\ [\text{m}]$ |
| :---: | :---: | :--- |
| **A – B** | 0.32 | $\sigma_z = 0.24 \cdot x \cdot \sqrt{1 + 0.001 \cdot x}$ |
| **C** | 0.22 | $\sigma_z = 0.20 \cdot x$ |
| **D** | 0.16 | $\sigma_z = \frac{0.14 \cdot x}{\sqrt{1 + 0.0003 \cdot x}}$ |
| **E – F** | 0.11 | $\sigma_z = \frac{0.08 \cdot x}{\sqrt{1 + 0.0015 \cdot x}}$ |

### 7.3 Rural vs. Urban Justification
* **Canonical Default:** **Briggs Rural** is the primary Phase 0 baseline because the underlying Pasquill-Gifford data were established over open rural terrain (Project Prairie Grass) and form the regulatory benchmark in EPA guideline models.
* **Urban Option:** The Urban formulation is implemented and unit-tested to support city-scale comparative benchmarks in subsequent phases.

### 7.4 Near-Source Region ($x < 100\ \text{m}$) & Spatial Regime Classification
* **Distance Regime Classification:**
  1. **$0 < x < 100\ \text{m}$ (Near-Source Engineering / Extrapolation Regime):** Below the documented empirical calibration range. Governed primarily by initial source geometry and engineering defaults; mathematical asymptote applies.
  2. **$100\ \text{m} \le x \le 10,000\ \text{m}$ (Briggs Empirical Core):** Calibrated from field tracer experiments (Prairie Grass, Round Hill, Porton Down).
  3. **$x > 10,000\ \text{m}$ (Far-Field Extrapolation Regime):** Outside documented empirical range; subject to regional empirical uncertainty.
* **Mathematical Property vs. Physical Theory:**
  * **Mathematical Fact:** The selected Briggs algebraic equations have the form $\sigma(x) = a x f(x)$ where $\lim_{x \to 0} f(x) = 1$, yielding the exact mathematical limit $\lim_{x \to 0^+} \frac{\sigma(x)}{x} = a$.
  * **Qualitative Theoretical Consistency:** This linear asymptote is qualitatively consistent with the short-time scaling described by Taylor's (1921) statistical dispersion theory ($\sigma \propto \sigma_v \cdot t$ for $t \ll T_L$).
  * **No Validation Claim:** The mathematical asymptote does **NOT** constitute empirical validation below $100\ \text{m}$. The region $x < 100\ \text{m}$ is strictly classified as an engineering/extrapolation regime.
* **Initial Source Dimensions ($\sigma_0 > 0$):**
  * In plume and puff simulations, total dispersion is evaluated as $\sigma_{\text{total}} = \sqrt{\sigma_0^2 + [\sigma^{\text{Briggs}}(x)]^2}$.
  * User-configurable finite initial source dimensions $(\sigma_{x0}, \sigma_{y0}, \sigma_{z0}) > 0$ (default $1.0\ \text{m}$) dominate over small turbulent dispersion near the source, preventing unphysical point singularities ($C \to \infty$) at $x=0$.
  * *Heuristic Reference:* In regulatory models (e.g. EPA ISC3 / AERMOD), volume source dimensions are initialized via $\sigma_{y0} \approx d / 4.3$ (assuming source width spans $4.3 \sigma \approx \pm 2.15 \sigma$). In AtmosSim, initial source widths are explicit, user-configurable parameters.
* **Range Utility:** AtmosSim provides `is_in_briggs_empirical_range(x)` in `atmosim.physics.dispersion` to programmatically flag whether receptor evaluations occur within the empirical core $[100, 10000]\ \text{m}$ or within the near-source / far-field extrapolation zones.

---

## 8. Mixing Height & Boundary Layer Specification (Holzworth Method)

### 8.1 Physical Concept
The mixing height $H_m$ is the vertical extent of the planetary boundary layer within which surface-emitted pollutants mix by convective and mechanical turbulence.

### 8.2 Holzworth (1972) Methodology
AtmosSim adopts the standard **Holzworth (1972)** radiosonde sounding intersection technique:
1. **Morning Mixing Height ($H_{m,\text{morning}}$):** Minimum morning surface temperature $+ 5^\circ\text{C}$ (urban heat island allowance) is extended along the dry adiabat ($\Gamma_d = 9.8^\circ\text{C/km}$) to its intersection with the morning upper-air temperature sounding.
2. **Afternoon Maximum Mixing Height ($H_{m,\text{afternoon}}$):** Maximum afternoon surface temperature is extended along the dry adiabat to its intersection with the morning sounding.

### 8.3 Scientific Scope Distinction: Phase 0 vs Phase 3
* **Phase 0 Requirement:** Establishes the literature-grounded methodology and mathematical specification.
* **Prohibition of Fabricated Sine Curves:** Atmospheric boundary layer height cannot be fabricated via arbitrary diurnal sine equations ($H(t) = H_0 + A\sin(\omega t)$).
* **Phase 3 Scope:** Operational general-location mixing-height calculation from ERA5 vertical soundings will be implemented in Phase 3.

---

## 9. Proof of Mass Flux Conservation & Multi-Domain Convergence

### 9.1 Analytical Derivation
Let total mass flux across any downwind $y-z$ plane be:

$$
F_{\text{mass}} = \int_{-\infty}^{\infty} \int_{0}^{\infty} u \, C(x, y, z) \, dz \, dy = Q
$$

Integrating the crosswind component $I_y = \int_{-\infty}^{\infty} \exp(-y^2/(2\sigma_y^2)) dy = \sqrt{2\pi}\sigma_y$.  
Integrating the vertical component $I_z = \int_{0}^{\infty} \left[ e^{-(z-H)^2/(2\sigma_z^2)} + e^{-(z+H)^2/(2\sigma_z^2)} \right] dz = \sqrt{2\pi}\sigma_z$.  
Combining:

$$
F_{\text{mass}} = u \cdot \left[ \frac{Q}{2\pi u \sigma_y \sigma_z} \right] \cdot (\sqrt{2\pi}\sigma_y) \cdot (\sqrt{2\pi}\sigma_z) = Q
$$

### 9.2 Numerical Multi-Domain Convergence Check
When evaluated numerically over a finite domain $D_k = [-k\sigma_y, k\sigma_y] \times [0, H + k\sigma_z]$, the captured mass flux converges monotonically toward $Q$:

| Domain Multiplier $k$ | Analytical Mass Capture Ratio $\text{erf}(k/\sqrt{2})$ | Numerical Flux (for $Q=100\ \text{g/s}$) | Relative Error to $Q$ |
| :---: | :---: | :---: | :---: |
| $k = 2$ | $95.45\%$ | $95.45\ \text{g/s}$ | $4.55\%$ |
| $k = 4$ | $99.9937\%$ | $99.99\ \text{g/s}$ | $< 0.01\%$ |
| $k = 6$ | $> 99.9999\%$ | $100.00\ \text{g/s}$ | $< 10^{-5}$ |
| $k = 8$ | $> 99.999999\%$ | $100.00\ \text{g/s}$ | $< 10^{-6}$ |

This convergence property is verified automatically in [`tests/test_plume.py`](../tests/test_plume.py) (`test_mass_flux_multi_domain_convergence`).

---

## 10. Equation Provenance Table

| Component | Selected Formulation | Primary Authoritative Source | Section / Equation | Evidence Level |
| :--- | :--- | :--- | :--- | :---: |
| **Gaussian Plume** | Steady-state point source with method-of-images reflection | Turner (1970); Seinfeld & Pandis (2016) | AP-26 / Chap. 18, Eq. 18.39–18.44 | Level 3 |
| **Stability Classification** | Pasquill-Gifford-Turner (PGT) | Pasquill (1961); Turner (1964); EPA ISC3 (1995) | *Met. Mag.* 90:33–49; *J. Appl. Met.* 3:83–91 | Level 3 |
| **Dispersion ($\sigma_y, \sigma_z$)** | Briggs (1973) Rural & Urban formulas | Briggs (1973) NOAA/ATDL Report No. 79 | ATDL-79, Table 1 (p. 6) | Level 3 |
| **Mixing Height** | Holzworth radiosonde dry-adiabat intersection | Holzworth (1972) | EPA AP-101 | Level 1 (Spec) |
| **Ground Reflection** | Method of images ($\partial C/\partial z = 0$ at $z=0$) | Sutton (1932); Turner (1970) | *Proc. R. Soc. A* 135:143; AP-26 | Level 3 |

---

## 11. Authoritative References

1. **Briggs, G. A. (1973).** *Diffusion Estimation for Small Emissions.* ATDL Report No. 79, Atmospheric Turbulence and Diffusion Laboratory, National Oceanic and Atmospheric Administration (NOAA), Oak Ridge, TN.
2. **Briggs, G. A. (1974).** *Diffusion Estimation for Small Emissions.* In: USAEC Report TID-26712, pp. 83–145.
3. **Gifford, F. A. (1961).** *Use of Routine Meteorological Observations for Estimating Atmospheric Dispersion.* Nuclear Safety, 2(4), 47–51.
4. **Gifford, F. A. (1976).** *Turbulent diffusion-typing schemes: A review.* Nuclear Safety, 17(1), 68–86.
5. **Holzworth, G. C. (1972).** *Mixing Heights, Wind Speeds, and Potential for Urban Air Pollution Throughout the Contiguous United States.* U.S. Environmental Protection Agency, Publication No. AP-101, Research Triangle Park, NC.
6. **McElroy, J. L., & Pooler, F. (1968).** *The St. Louis Dispersion Study: Volume II - Analysis.* National Air Pollution Control Administration, Publication No. AP-53.
7. **Pasquill, F. (1961).** *The estimation of the dispersion of windborne material.* The Meteorological Magazine, 90(1063), 33–49.
8. **Seinfeld, J. H., & Pandis, S. N. (2016).** *Atmospheric Chemistry and Physics: From Air Pollution to Climate Change* (3rd ed.). John Wiley & Sons, Hoboken, NJ. Chapter 18: Atmospheric Diffusion.
9. **Sutton, O. G. (1932).** *A theory of eddy diffusion in the atmosphere.* Proceedings of the Royal Society of London. Series A, 135(828), 143–165.
10. **Turner, D. B. (1964).** *A Diffusion Model for an Urban Area.* Journal of Applied Meteorology, 3(1), 83–91.
11. **Turner, D. B. (1970).** *Workbook of Atmospheric Dispersion Estimates.* U.S. Environmental Protection Agency, Office of Air Programs Publication No. AP-26.
12. **U.S. EPA (1995).** *User's Guide for the Industrial Source Complex (ISC3) Dispersion Models: Volume II - Description of Model Algorithms.* EPA-454/B-95-003b, U.S. Environmental Protection Agency, Research Triangle Park, NC.
13. **U.S. EPA (1999).** *Meteorological Monitoring Guidance for Regulatory Modeling Applications.* EPA-454/R-99-005, U.S. Environmental Protection Agency, Research Triangle Park, NC.
