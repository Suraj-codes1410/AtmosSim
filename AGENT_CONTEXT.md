# AtmosSim — Comprehensive Agent Context Document

> **Purpose:** This document gives a new agent complete working context for the AtmosSim project.
> It captures the repository structure, all implementation decisions, scientific foundations,
> test suite status, active constraints, and the exact state of every completed phase.
> Read this before making any changes.

---

## 0. Project Identity

| Property | Value |
|---|---|
| **Project Name** | AtmosSim |
| **Repository** | `https://github.com/Suraj-codes1410/AtmosSim.git` (remote: `origin/main`) |
| **Local Path** | `/home/suraj/AtmosSim` |
| **Python Package** | `atmosim` (installed in editable mode, src‑layout) |
| **Language** | Python 3.10+ |
| **OS** | Linux (Ubuntu, user `suraj`) |
| **Description** | Research‑grade, physics‑based atmospheric dispersion simulator and reproducible physics‑to‑ML benchmark framework for PM2.5 forecasting |

---

## 1. Environment Setup

### 1.1 Virtualenv
```
/home/suraj/atmosIQ/venv
```
Python 3.14.4, with: `numpy`, `scipy`, `matplotlib`, `pytest`, `pyproj`, `requests`.

### 1.2 System Python
`/usr/bin/python3` (Python 3.14.4) — all packages are also installed system‑wide so that bare `pytest` (which resolves to `/usr/bin/pytest`) works without activating the venv.

### 1.3 Running Tests
Both of the following work and produce identical results:
```bash
pytest -v                                         # system Python
/home/suraj/atmosIQ/venv/bin/pytest -v           # virtualenv Python
```

### 1.4 pyproject.toml Dependencies
```toml
dependencies = [
    "numpy>=1.22.0",
    "scipy>=1.8.0",
    "matplotlib>=3.5.0",
    "pyproj>=3.0.0",
    "requests>=2.28.0",
]
```
`pytest` and `pytest-cov` are in `[project.optional-dependencies] dev`.
`pythonpath = ["src"]` is set in `[tool.pytest.ini_options]`, so `import atmosim` resolves automatically during tests.

---

## 2. Repository Layout

```
AtmosSim/
├── AGENT_CONTEXT.md               ← this file (artifact)⟶
├── README.md                      ← badges: 179 passed, Phase 2 Frozen
├── pyproject.toml
│
├── src/
│   └── atmosim/
│       ├── __init__.py
│       │
│       ├── physics/               ← Phase 0 + Phase 1 (FROZEN)
│       │   ├── stability.py       ← PGT A–F stability classification
│       │   ├── dispersion.py      ← Briggs sigma_y / sigma_z parameterizations
│       │   ├── plume.py           ← Steady‑state Gaussian Plume solver
│       │   ├── puff.py            ← Time‑dependent Gaussian Puff engine
│       │   ├── puff_lifecycle.py  ← Puff culling, SpatialBounds, lifecycle FSM
│       │   └── coordinates.py     ← WGS84 ↔ local Cartesian (UTM via pyproj)
│       │
│       ├── data/                  ← Phase 2 (FROZEN)
│       │   ├── cache.py           ← Deterministic SHA‑256 JSON file cache
│       │   ├── open_meteo.py      ← Open‑Meteo hourly meteorology connector
│       │   ├── terrain.py         ← DEM / elevation grid connector & interpolation
│       │   └── overpass.py        ← OSM / Overpass QL road & industrial proxy connector
│       │
│       ├── sources/               ← Phase 2 (FROZEN)
│       │   ├── models.py          ← RoadSegmentProxy, IndustrialProxy, PointSourceProxy
│       │   ├── provenance.py      ← SourceProvenance, UncertaintyClass (LOW/MEDIUM/HIGH)
│       │   ├── traffic_profiles.py← Diurnal 24h traffic profiles (normalized)
│       │   └── emissions.py       ← RoadNetworkSegmenter, ProxyEmissionParameterizer
│       │
│       ├── simulation/            ← Phase 2 (FROZEN)
│       │   └── input_assembler.py ← SimulationInputAssembler, SimulationInput, InputManifest
│       │
│       └── visualization/         ← Diagnostic plotting (all phases)
│           ├── plume.py           ← plot_plume_2d, plot_crosswind_slice, plot_downwind_centerline
│           ├── puff.py            ← plot_puff_trajectories, plot_puff_concentration_field, etc.
│           └── environmental.py   ← plot_meteorological_time_series, plot_source_network_and_terrain
│
├── tests/
│   ├── fixtures/                  ← Offline JSON fixtures (no live API calls needed)
│   │   ├── sample_open_meteo.json
│   │   ├── sample_overpass_roads.json
│   │   └── sample_elevation.json
│   │
│   ├── test_stability.py          ← 45 tests — PGT classification
│   ├── test_dispersion.py         ← 45 tests — Briggs sigma, Briggs range checks
│   ├── test_plume.py              ← 26 tests — Plume physics, mass flux, analytical refs
│   ├── test_puff.py               ← 17 tests — Puff advection, superposition, convergence
│   ├── test_puff_lifecycle.py     ←  6 tests — Culling, memory boundedness
│   ├── test_puff_stability.py     ←  8 tests — Stability × puff dispersion growth
│   ├── test_coordinates.py        ← 10 tests — WGS84 ↔ UTM round‑trip
│   ├── test_open_meteo.py         ←  6 tests — Meteo parsing, circular wind interpolation
│   ├── test_terrain.py            ←  4 tests — Bilinear interpolation, fallback
│   ├── test_overpass.py           ←  3 tests — OSM road parsing, geodesic length
│   ├── test_emissions.py          ←  7 tests — Q(t) dimensionality, mass conservation (weekday/weekend)
│   └── test_input_assembler.py    ←  4 tests — Assembly, Phase 1 coupling, mass conservation
│
├── scripts/
│   ├── generate_plume_diagnostics.py    ← Phase 0 diagnostic figures
│   ├── generate_puff_diagnostics.py     ← Phase 1 diagnostic figures
│   └── generate_phase2_diagnostics.py   ← Phase 2 diagnostic figures (uses offline fixtures)
│
├── docs/
│   ├── phase0_completion_report.md
│   ├── physics_references.md
│   ├── physics_parameterization_audit.md
│   ├── phase1_completion_report.md
│   ├── phase1_physics_references.md
│   ├── phase2_architecture.md
│   ├── phase2_data_sources.md
│   ├── phase2_emission_parameterization.md
│   ├── phase2_provenance.md
│   └── phase2_completion_report.md
│
└── sample_plots/                  ← Generated diagnostic PNG figures (16 total)
```

---

## 3. Current Phase Status

| Phase | Name | Status | Tests |
|---|---|---|---|
| **Phase 0** | Gaussian Plume Analytical Baseline | ✅ FROZEN | 116 |
| **Phase 1** | Time‑Dependent Gaussian Puff Engine | ✅ FROZEN | 39 |
| **Phase 2** | Environmental & Source Input Assembly | ✅ FROZEN | 24 |
| **Phase 3** | Meteorological Assimilation & Complex Flow Realism | 🔲 NOT STARTED | — |
| **Phase 4** | Observational Validation (CAAQMS) | 🔲 NOT STARTED | — |

**Total test suite: 179 passed, 0 failed, 0 warnings** (`pytest -q`, 3.62 s)

---

## 4. Phase 0 — Gaussian Plume Analytical Baseline

### 4.1 What Was Built

**Module: `src/atmosim/physics/stability.py`**
- `StabilityClass` enum: A (very unstable), B, C, D (neutral), E, F (very stable)
- `classify_stability(wind_speed, daytime, cloud_cover, solar_radiation, solar_elevation)` → `StabilityClass`
- Implements the Pasquill‑Gifford‑Turner (PGT) classification from Turner (1964) and EPA ISC3 (1995)
- Insolation categorized as Strong / Moderate / Slight based on solar irradiance thresholds (>600, 300–600, <300 W m⁻²)

**Module: `src/atmosim/physics/dispersion.py`**
- `EnvironmentType` enum: `RURAL`, `URBAN`
- `compute_sigma_y(x, stability, environment)` → float [m]
- `compute_sigma_z(x, stability, environment)` → float [m]
- `compute_dispersion_coefficients(x, stability, environment)` → Tuple[float, float]
- Briggs (1973, 1974) algebraic parameterisations for both rural and urban surface regimes, classes A–F
- `BRIGGS_MIN_X = 100.0 m`, `BRIGGS_MAX_X = 10 000.0 m` — empirical calibration range explicitly defined
- `is_in_briggs_empirical_range(x)` — programmatic range‑check

**Module: `src/atmosim/physics/plume.py`**
- `gaussian_plume_concentration(y, z, Q, wind_speed, effective_height, sigma_y, sigma_z)` → float [g m⁻³]
- `GaussianPlumeModel` high‑level class
- Governing equation: 
  $$C = \frac{Q}{2\pi u \sigma_y \sigma_z}\exp\!\left(-\frac{y^2}{2\sigma_y^2}\right)\!\left[\exp\!\left(-\frac{(z-H)^2}{2\sigma_z^2}\right) + \exp\!\left(-\frac{(z+H)^2}{2\sigma_z^2}\right)\right]$$

### 4.2 Scientific Verification (Phase 0)
- **Advective mass‑flux conservation:** $\iint u\,C\,dy\,dz = Q$ verified via `scipy.integrate.dblquad`, recovering $Q=100 \text{g s}^{-1}$ within <0.01 % across expanding multi‑σ domains.
- **Three independently‑derived analytical reference cases** matching to `rtol=10⁻¹⁰`.
- **Physical symmetries:** emission linearity, cross‑wind symmetry, ground‑reflection doubling — all verified to `rtol=10⁻¹²`.
- **Known limitation:** Longitudinal dispersion $\sigma_x$ deferred to Phase 1.

### 4.3 What Is Not in Phase 0
- Time‑dependent advection, puff parcels, variable wind, geographic coordinates, observational validation.

---

## 5. Phase 1 — Time‑Dependent Gaussian Puff Engine

### 5.1 What Was Built

**Module: `src/atmosim/physics/puff_lifecycle.py`**
```python
@dataclass(frozen=True)
class PuffLifecycleState(str, Enum):
    CREATED, ACTIVE, CULLED

@dataclass(frozen=True)
class SpatialBounds:
    x_min, x_max, y_min, y_max, z_min, z_max: float

@dataclass(frozen=True)
class PuffLifecycleConfig:
    max_age: float = 7200.0        # seconds
    max_distance: float = 50000.0  # meters
    min_mass: float = 1e-8         # grams
    bounds: Optional[SpatialBounds] = None
```

**Module: `src/atmosim/physics/puff.py`** — Core engine
- `WindField` dataclass: constant or time‑varying wind; `WindField.constant(u, v)` and `WindField.from_time_series(times, u_vals, v_vals)`
- `EmissionSource` dataclass: `source_id`, `x`, `y`, `z`, `emission_rate` (float or callable), `release_interval`
- `GaussianPuff` dataclass: position, mass, $\sigma_x$, $\sigma_y$, $\sigma_z$, age, travel distance, state, cull reason
- `GaussianPuffConfig` frozen dataclass: `time_step`, `stability`, `environment`, `calm_wind_threshold`, `include_ground_reflection`, `mass_decay_rate`, **`lifecycle_config`**
- `GaussianPuffEngine` class: `add_source()`, `step(dt, wind)`, `run(duration, wind, dt)`, `evaluate(x_rec, y_rec, z_rec)`, `reset()`
- `evaluate_gaussian_puff_concentration()` — vectorised single‑puff receptor evaluation

**Module: `src/atmosim/physics/coordinates.py`**
- `LocalCoordinateSystem(origin_lat, origin_lon)` — pyproj‑based WGS84 → UTM → local Cartesian
- `geo_to_cartesian(lat, lon)` → `(x_m, y_m)`; `cartesian_to_geo(x, y)` → `(lat, lon)`
- Round‑trip consistency: sub‑millimeter (<10⁻⁴ m).

### 5.2 Key Scientific Decisions & Provenance
| Claim | Classification | Literature Basis |
|---|---|---|
| $\sigma_x = \sigma_y$ (horizontal isotropy) | Engineering approximation | Taylor (1921), Batchelor (1950, 1952), Gifford (1976), CALPUFF (Scire et al., 2000) |
| Briggs $\sigma_y/\sigma_z$ as function of cumulative travel distance $s(t)$ | Scientifically defensible (equivalent‑path‑length method) | Ludwig et al. (1977), Zannetti (1990) |
| $u_{\text{min}} = 0.1 \text{m s}^{-1}$ and $s_{\text{eff}}$ floor | **Numerical regularisations** (engineering safeguards) | Prevent division‑by‑zero during calm periods |
| Spatial wind uniformity in Phase 1 | Explicit assumption (documented) | Deferred to Phase 3 |
| Briggs empirical range $100 \text{m}\le x\le10 000 \text{m}$ | Empirical calibration range (field data) | Prairie Grass, Round Hill experiments |
| Near‑source $s<100 \text{m}$ | Engineering/extrapolation regime (not empirically validated) | Mathematical asymptote vs physical data |

### 5.3 Governing Equations
**3D Gaussian Puff concentration:**
$$C_p = \frac{M(t)}{(2\pi)^{3/2}\sigma_x\sigma_y\sigma_z}\exp\!\left(-\frac{(x-x_p)^2}{2\sigma_x^2}-\frac{(y-y_p)^2}{2\sigma_y^2}\right)\!\left[\exp\!\left(-\frac{(z-z_p)^2}{2\sigma_z^2}\right)+\exp\!\left(-\frac{(z+z_p)^2}{2\sigma_z^2}\right)\right]$$

**Dispersion growth (equivalent path length):**
$$\sigma_y(s) = \sqrt{\sigma_{y0}^2 + \bigl[\sigma_y^{\text{Briggs}}(s_{\text{eff}})\bigr]^2},\quad \sigma_x = \sigma_y,\quad \sigma_z(s) = \sqrt{\sigma_{z0}^2 + \bigl[\sigma_z^{\text{Briggs}}(s_{\text{eff}})\bigr]^2}$$
where $s(t)=\int |\mathbf{U}|\,dt$ is the integrated Lagrangian path length.

**Mid‑point trajectory integration (2nd‑order):**
$$\mathbf{x}_p(t+\Delta t) = \mathbf{x}_p(t) + \mathbf{U}\!\left(\mathbf{x}_p + \tfrac{1}{2}\mathbf{U}\Delta t,\; t+\tfrac{1}{2}\Delta t\right)\Delta t$$

### 5.4 Numerical Verification (Phase 1)
- **Second‑order convergence:** halving $\Delta t$ reduces trajectory error by factor 4.0 exactly (orders $\mathcal{O}(\Delta t^2)$).
- **Rotating wind analytical test:** positional discrepancy <0.01 m over 50 s rotation.
- **3D spatial mass integral:** recovers $M=250 \text{g}$ with `rtol<10⁻⁶` (3‑D Simpson integration).
- **Emission mass conservation:** $N\times Q\times\Delta t_{\text{rel}}$ matches engine‑integrated mass to `rtol=10⁻¹²`.
- **Calm‑wind stability:** finite, non‑divergent behavior at $u=0 \text{m s}^{-1}$.
- **All 6 PGT stability classes × RURAL/URBAN:** stable behaviour confirmed.

### 5.5 Puff Lifecycle & Memory Boundedness
- State machine: `CREATED → ACTIVE → CULLED`
- Culling triggered by: `MAX_AGE`, `MAX_DISTANCE`, `MIN_MASS`, `DOMAIN_BOUNDS`
- Culling is a **computational domain management technique** — NOT a physical removal.
- Active puff count stabilises (bounded) for continuous sources; `PuffLifecycleStats` tracks all counts.

---

## 6. Phase 2 — Environmental & Source Input Assembly

### 6.1 What Was Built

**Data connectors (`src/atmosim/data/`):**
- `cache.py` — `DataCache` (deterministic SHA‑256 JSON caching, location `/home/suraj/AtmosSim/.cache/atmosim/`)
- `open_meteo.py` — `OpenMeteoConnector`, `MeteorologicalTimeSeries`
  - Ingests hourly wind speed, direction, temperature, humidity, boundary‑layer height, pressure, direct normal irradiance, cloud cover.
  - **Circular wind interpolation** eliminates the 359°→1° jump:
    $$u_{\text{interp}}=(1-\alpha)\cos\theta_0+\alpha\cos\theta_1,\quad v_{\text{interp}}=(1-\alpha)\sin\theta_0+\alpha\sin\theta_1$$
    $$\theta(t)=\bigl(\operatorname{atan2}(v_{\text{interp}},u_{\text{interp}})\times180/\pi+360\bigr)\bmod 360$$
  - `.to_wind_field()` → `WindField` compatible with Phase 1.
- `terrain.py` — `TerrainConnector`, `TerrainField`
  - 2‑D gridded DEM ingestion, 2‑D bilinear + nearest‑neighbor interpolation.
  - `synthetic_planar()` generates analytical flat terrain for offline tests.
- `overpass.py` — `OverpassConnector`, `RawOsmFeature`
  - Queries OSM for road ways, industrial polygons, and point sources.
  - Returns a list of `RawOsmFeature` objects with `.feature_category`.

**Source proxies (`src/atmosim/sources/`):**
- `models.py` defines `RoadSegmentProxy`, `IndustrialProxy`, `PointSourceProxy` (all with geographic and Cartesian coordinates, plus provenance fields).
- `provenance.py` provides `SourceProvenance` and `UncertaintyClass` (LOW/MEDIUM/HIGH).
- `traffic_profiles.py` supplies a diurnal 24‑hour traffic multiplier curve (morning/evening peaks) **strictly normalised** ($\frac{1}{24}\sum f_h = 1$) with a weekend multiplier of 0.85.
- `emissions.py` implements `RoadNetworkSegmenter`, `ProxyEmissionParameterizer`, and `RoadEmissionConfig`.

### 6.2 Governing Emission Formula
$$Q_{\text{road}}(t) = L_{\text{km}} \times \underbrace{\bigl(\text{AADT}_{\text{class}} \times \tfrac{f(t)}{24}\bigr)}_{V(t)\,[\text{veh hr}^{-1}]} \times \text{EF} \times \frac{1}{3600}\quad[\text{g PM}_{2.5}\,\text{s}^{-1}]$$
where:
- $L_{\text{km}}$ = road segment length in km
- `AADT` = annual average daily traffic (proxy estimate, see Table below)
- $f(t)$ = hourly traffic multiplier (normalised)
- `EF` = emission factor (g veh⁻¹ km⁻¹)
- Weekend multiplier = 0.85.

**Emission factor table (audited vs EMEP/EEA 2019, CPCB/ARAI 2018):**
| Highway class | EF [g veh⁻¹ km⁻¹] | AADT proxy [veh day⁻¹] | Rationale |
|---|---|---|---|
| motorway | 0.22 | 45 000 | High HDV %, high speed, elevated tyre wear |
| trunk | 0.18 | 30 000 | Inter‑city freight + bus |
| primary | 0.14 | 20 000 | Urban arterial, stop‑and‑go, mixed fleet |
| secondary | 0.10 | 10 000 | City collector, low HDV |
| tertiary | 0.08 | 4 000 | Urban distributor, light‑duty dominant |
| residential | 0.05 | 1 200 | Low‑speed neighbourhood |
| service | 0.03 | 400 | Parking alleys, access ways |

**Pollutant scope:** Primary exhaust PM2.5 + brake wear + tyre wear. **Excludes** road‑dust resuspension (AP‑42 silt loading).

**AADT is a proxy:** OSM does not provide traffic counts. AADT defaults are engineering estimates from IRC:106‑1990 and Guttikunda et al. (2014). Users can override via `RoadEmissionConfig(aadt_by_class=…)`.

**Initial road source dimensions $\sigma_0=(5,5,1.5)\,$ m:**
- Based on EPA CALINE4 / AERMOD conventions (volume‑source mixing‑zone heuristic): $\sigma_{y0}\approx W/2.15$ where $W$≈10‑20 m lane width → 5 m; $\sigma_{z0}\approx H_{\text{wake}}/2.15≈1.5$ m.
- Horizontal isotropy: $\sigma_{x0}=\sigma_{y0}=5$ m.
- User‑configurable via `RoadEmissionConfig(initial_sigma=…)`.

**Road segmentation:** Max segment length = 250 m; each segment placed at its geometric midpoint (z≈0.5 m).

**Simulation assembly (`src/atmosim/simulation/input_assembler.py`):**
- `SimulationInput` dataclass holds coordinate system, meteorology, terrain, source lists, provenance, domain radius, start/end times, manifest, and a SHA‑256 `input_hash`.
- `SimulationInputAssembler` builds a complete `SimulationInput` from lat/lon, date range, and optional overrides (e.g., `allow_synthetic_sources_on_empty`).

### 6.3 Industrial Proxy Safety Rule
**Industrial polygons and chimneys are NEVER added to `sim_input.sources`.** They are retained only in `sim_input.industrial_proxies` with `emission_status='unavailable'`. This is enforced by the test `test_industrial_proxies_do_not_inject_fabricated_emissions`.

### 6.4 Mass‑Conservation Q(t) → M (Verified)
1. **Integral test (test_emissions.py):** For a 1 km primary road segment:
   - Weekday (Wed Aug 5): $\sum Q(t_i)\Delta t = 2 800 \text{g}$ (= 1 km × 20 000 veh day⁻¹ × 0.14 g veh⁻¹ km⁻¹).
   - Weekend (Sat Aug 1): 2 380 g (= 2800 g × 0.85) ✅ (rel error < 0.1 %).
2. **Puff engine coupling test (test_input_assembler.py):** `sum(puff.mass)` equals `sum(Q(t_k)·release_interval)` to `rtol=10⁻⁶` ✅.

### 6.5 Coordinate Convention (All Phases)
- **Origin:** `(origin_lat, origin_lon)` — domain centre.
- **+x:** East (meters)
- **+y:** North (meters)
- **+z:** Up from ground (meters)
- **Projection:** Auto‑selected UTM zone via `pyproj` (EPSG:326xx or EPSG:327xx).
- **Unit contract:** All physics inputs/outputs are in SI metres. No degrees appear in the physics layer.

### 6.6 Fallback / Offline Behaviour
- `allow_synthetic_sources_on_empty=True` (default): if Overpass returns no roads, a synthetic `highway=primary` segment is created to guarantee non‑zero sources for testing.
- All connectors work offline with cached JSON fixtures in `tests/fixtures/`.

---

## 7. Test Suite Summary

| File | Count | What Is Tested |
|---|---|---|
| `test_stability.py` | 45 | PGT A–F classification, insolation categories, cloud‑cover handling, edge cases |
| `test_dispersion.py` | 45 | Briggs $\sigma_y/\sigma_z$ for all classes × environments, range checks, distance validation |
| `test_plume.py` | 26 | Gaussian plume invariants, mass flux, 3 analytical reference cases, scaling laws |
| `test_puff.py` | 17 | Puff physics, Lagrangian advection, mass conservation, convergence, superposition |
| `test_puff_lifecycle.py` | 6 | Age/distance/mass/bounds culling, memory stabilisation |
| `test_puff_stability.py` | 8 | All PGT classes × puff dispersion growth, urban vs rural |
| `test_coordinates.py` | 10 | WGS84 ↔ Cartesian round‑trip across 5 global cities |
| `test_open_meteo.py` | 6 | Meteo parsing, circular wind interpolation across 359°→1° boundary |
| `test_terrain.py` | 4 | Bilinear exactness on synthetic planar terrain, fallback generation |
| `test_overpass.py` | 3 | OSM road parsing, geodesic length calculation |
| `test_emissions.py` | 7 | EF dimensional correctness, AADT scaling, diurnal normalisation, mass integral (weekday + weekend), industrial isolation |
| `test_input_assembler.py` | 4 | Full assembly, manifest generation, Phase 1 engine coupling, Q→M mass conservation |
| **TOTAL** | **179** | **All passing, 0 failures, 0 warnings** |

---

## 8. Diagnostic Scripts & Sample Plots

| Script | Output Figures |
|---|---|
| `scripts/generate_plume_diagnostics.py` | `gaussian_plume_baseline.png`, `stability_comparison.png`, `wind_comparison.png`, `emission_comparison.png`, `crosswind_slice.png`, `downwind_centerline.png` |
| `scripts/generate_puff_diagnostics.py` | `puff_single_constant_wind.png`, `puff_rotating_wind.png`, `puff_wind_reversal.png`, `puff_stability_growth.png`, `puff_multi_source.png`, `puff_lifecycle_memory.png` |
| `scripts/generate_phase2_diagnostics.py` | `phase2_meteo_timeseries.png`, `phase2_sources_and_terrain.png`, `phase2_puff_simulation_snapshot.png` |

All scripts use offline fixtures and require no live API calls.

---

## 9. Scientific Assumptions & Known Limitations (All Phases)

### Active Assumptions
1. **Passive PM2.5 tracer:** No secondary aerosol formation, no gas‑phase chemistry, no dry/wet deposition.
2. **Spatially uniform wind:** Wind vector is spatially uniform across the local domain per timestep (Phase 1 assumption, documented).
3. **Flat ground boundary:** Ground reflection via method of images ($\partial C/\partial z=0$ at $z=0$); no terrain‑following flow.
4. **Horizontal isotropy:** $\sigma_x = \sigma_y$ (standard Gaussian puff approximation, documented literature basis).
5. **No secondary road dust:** AP‑42 silt‑loading mechanism excluded from emission factors.

### Explicitly Deferred to Later Phases
- **Phase 3:** Spatially varying wind fields, PBL‑height‑aware vertical mixing, terrain‑flow interactions, meteorological assimilation.
- **Phase 4:** Observational validation against CAAQMS or other ground‑monitoring stations.

### Numerical Regularisations (NOT Physical Laws)
- `u_min = 0.1 m s⁻¹` — prevents division‑by‑zero during calm wind.
- `s_eff = max(s(t), u_min·age, 1.0 m)` — prevents Briggs $\sigma$ singularity at $s=0$.

### Briggs Parameterisation Validity
- **Empirical range:** $100 \text{m} \le x \le 10 000 \text{m}$ (field tracer calibration: Prairie Grass, Round Hill).
- **Below 100 m:** Extrapolation / engineering regime — initial $\sigma_0$ dominates, mathematically continuous but **not empirically validated**.
- **Above 10 km:** Far‑field extrapolation, no tracer data.

---

## 10. Key API Contracts to Respect

### GaussianPuffEngine
```python
engine = GaussianPuffEngine(config=GaussianPuffConfig(...))
engine.add_source(EmissionSource(
    source_id="src1", x=0.0, y=0.0, z=10.0,
    emission_rate=50.0,               # float OR callable(t) → float, [g/s]
    release_interval=10.0             # seconds between discrete puff releases
))
engine.run(duration=3600.0, wind=WindField.constant(u=4.0, v=0.0), dt=5.0)
conc = engine.evaluate(x_rec, y_rec, z_rec)  # → np.ndarray [g/m³]
```

### SimulationInputAssembler
```python
sim_input = assembler.build(
    latitude=28.6139, longitude=77.2090,
    start_time=..., end_time=...,
    domain_radius_m=5000.0,
    terrain_resolution_m=250.0,            # optional
    max_segment_length_m=250.0,            # optional
    allow_synthetic_sources_on_empty=True # optional
)
engine = sim_input.to_puff_engine(config=GaussianPuffConfig(time_step=5.0))
wind   = sim_input.get_wind_field()
engine.run(duration=3600.0, wind=wind)
```

### PuffLifecycleConfig — Correct Field Names
```python
PuffLifecycleConfig(
    max_age=7200.0,          # seconds (NOT max_age_seconds)
    max_distance=50000.0,    # meters (NOT max_distance_meters)
    min_mass=1e-8,
    bounds=SpatialBounds(...),  # (NOT spatial_bounds)
)
```
⚠️ Using the old names raises `TypeError`.

### GaussianPuffConfig — lifecycle_config is a **field**, not a constructor argument
```python
# CORRECT
config = GaussianPuffConfig(time_step=5.0, lifecycle_config=my_lifecycle_cfg)
engine = GaussianPuffEngine(config=config)

# WRONG – will raise TypeError
engine = GaussianPuffEngine(config=config, lifecycle_config=my_lifecycle_cfg)
```

### evaluate vs evaluate_concentration
The concentration evaluation method on `GaussianPuffEngine` is named **`engine.evaluate()`**, **not** `engine.evaluate_concentration()`.

---

## 11. Important File Paths

| Purpose | Path |
|---|---|
| Core puff engine | `src/atmosim/physics/puff.py` |
| Puff lifecycle & culling | `src/atmosim/physics/puff_lifecycle.py` |
| Dispersion coefficients | `src/atmosim/physics/dispersion.py` |
| Stability classification | `src/atmosim/physics/stability.py` |
| Gaussian plume (steady‑state) | `src/atmosim/physics/plume.py` |
| Coordinate transforms | `src/atmosim/physics/coordinates.py` |
| Open‑Meteo connector | `src/atmosim/data/open_meteo.py` |
| Terrain/DEM connector | `src/atmosim/data/terrain.py` |
| OSM/Overpass connector | `src/atmosim/data/overpass.py` |
| SHA‑256 file cache | `src/atmosim/data/cache.py` |
| Road emission parameterizer | `src/atmosim/sources/emissions.py` |
| Source proxy models | `src/atmosim/sources/models.py` |
| Provenance tracking | `src/atmosim/sources/provenance.py` |
| Diurnal traffic profiles | `src/atmosim/sources/traffic_profiles.py` |
| Simulation assembler | `src/atmosim/simulation/input_assembler.py` |
| Plume visualization | `src/atmosim/visualization/plume.py` |
| Puff visualization | `src/atmosim/visualization/puff.py` |
| Environmental visualization | `src/atmosim/visualization/environmental.py` |
| Offline test fixtures | `tests/fixtures/` |
| Phase 0 docs | `docs/phase0_completion_report.md` |
| Phase 1 docs | `docs/phase1_completion_report.md` |
| Phase 2 docs | `docs/phase2_completion_report.md` |

---

## 12. What NOT to Do (Hard Rules)
1. **Do NOT modify any file in `src/atmosim/physics/`** without explicit user instruction — Phases 0 & 1 are scientifically frozen.
2. **Do NOT add new physics** to Phase 0 or Phase 1 modules under the guise of a “fix”.
3. **Do NOT fabricate emission rates** for industrial proxies. They must remain `emission_status='unavailable'`.
4. **Do NOT commit or push** to git unless the user explicitly says to.
5. **Do NOT silently change unit conventions.** All distances are metres, emissions are g s⁻¹, concentrations are g m⁻³.
6. **Do NOT extrapolate Briggs parameterisations** beyond $x=10 000 \text{m}$ without documenting it as a far‑field extrapolation.
7. **Do NOT call `engine.evaluate_concentration()`** — it does not exist. Use `engine.evaluate()`.
8. **Do NOT treat AADT values as measured traffic counts** — they are engineering proxy estimates.

---

## 13. Git / Version Control Status
```
Remote:  origin → https://github.com/Suraj-codes1410/AtmosSim.git
Branch:  main
```
Phase 0 and Phase 1 were committed and pushed in **10 clean commits**.  
Phase 2 changes are **uncommitted** (per user instruction at time of implementation).

**Before Phase 3:** Confirm with the user whether to commit Phase 2.

---

## 14. Reference Literature (Key)
| Reference | Role in AtmosSim |
|---|---|
| Turner, D.B. (1970). EPA AP‑26 | Gaussian plume governing equation |
| Seinfeld & Pandis (2016), Ch. 18 | Atmospheric dispersion physics |
| Briggs, G.A. (1973, 1974). ATDL‑79 | $\sigma_y$, $\sigma_z$ parameterisation formulas |
| Gifford, F.A. (1976). Nuclear Safety 17(1) | Stability‑class diffusion review |
| U.S. EPA ISC3 (1995). EPA‑454/B‑95‑003b | Regulatory plume + volume‑source guidance |
| Taylor, G.I. (1921). Proc. London Math. Soc. | Statistical turbulence diffusion theory |
| Batchelor, G.K. (1950). QJRMS 76 | Atmospheric diffusion similarity theory |
| Scire et al. (2000). CALPUFF User Guide | Puff lifecycle, $\sigma_x=\sigma_y$ convention |
| Zannetti, P. (1990). Air Pollution Modeling | Gaussian puff modelling, Ch. 6 |
| Ludwig et al. (1977). Atmos. Environ. 11(5) | Equivalent path length / cumulative travel distance |
| EMEP/EEA Guidebook (2019) | PM2.5 road emission factors (exhaust + non‑exhaust) |
| CPCB & ARAI (2018) | Indian fleet composite PM2.5 emission factors |
| EPA CALINE4 / AERMOD / ISC3 | Volume‑source initial mixing‑zone (σ₀ = W/2.15) |

---

## 15. Phase 3 Scope (Next Phase — NOT YET STARTED)
Based on the project roadmap, Phase 3 is expected to cover:
- **Spatially varying meteorological fields** — gridded wind, temperature, humidity inputs.
- **PBL‑height‑aware vertical mixing** — using ingested PBLH from Open‑Meteo.
- **Complex terrain‑flow interactions** — terrain elevation influencing wind streamlines.
- **Meteorological assimilation** — coupling ERA5 / Open‑Meteo reanalysis to the physics engine.
- **Potentially:** Dry deposition parameterisation for PM2.5.

**Do not begin Phase 3 without explicit user instruction.**

---

*Last updated: 2026‑09‑02 | Test suite: 179 passed | Phases 0‑2 frozen*
