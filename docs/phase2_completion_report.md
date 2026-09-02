# AtmosSim Phase 2 Completion & Scientific Audit Report

## 1. Executive Summary

Phase 2 establishes the **General-Location Environmental & Source Input Assembly** pipeline for AtmosSim. It enables transforming an arbitrary geographic coordinate `(lat, lon)` and continuous simulation date range into a fully normalized, validated, provenance-complete `SimulationInput` dataset consumable by the frozen Phase 1 Gaussian Puff engine.

All **179 automated unit, numerical, and integration tests** pass with 0 failures and 0 warnings.

---

## 2. Phase 2 Objective

To build an environmental and source data ingestion architecture that provides scientifically defensible, traceable, and unit-consistent inputs to the Phase 1 dispersion solver without modifying the underlying physics.

---

## 3. Architecture

* **Layered Pipeline:** Decoupled external connectors (`open_meteo.py`, `terrain.py`, `overpass.py`), source proxy models (`models.py`, `emissions.py`, `traffic_profiles.py`, `provenance.py`), and the core input assembler (`input_assembler.py`).
* **Canonical Coordinate System:** Anchored metric Cartesian UTM frame (+x=East, +y=North in meters) via `LocalCoordinateSystem`.
* **Physics Interface:** Seamless export to the frozen Phase 1 `GaussianPuffEngine` via `sim_input.to_puff_engine()` and `sim_input.get_wind_field()`.

---

## 4. Environmental Data Pipeline

* **Open-Meteo Weather Integration:** Ingestion of hourly wind speed, wind direction, dry-bulb temperature, relative humidity, surface pressure, solar radiation, and boundary layer height (PBLH).
* **Missing-Data Handling:** Configurable policies (`FAIL_FAST` vs. `INTERPOLATE_OR_FORWARD_FILL`) with explicit audit tracking.

---

## 5. Meteorological Integration

* **Continuous Time Interpolation:** Continuous scalar interpolation for wind speed, temperature, and humidity.
* **Circular Trigonometric Interpolation:** Direction vectors interpolated via unit trigonometric components:
  $$u_{\text{interp}} = \text{interp}(\cos\theta), \quad v_{\text{interp}} = \text{interp}(\sin\theta)$$
  $$\theta_{\text{interp}} = \text{atan2}(v_{\text{interp}}, u_{\text{interp}}) \pmod{360}$$
  eliminating angular jump discontinuities across the 359° → 0° boundary.

---

## 6. Terrain Integration

* **2D Gridded Elevation Model (`TerrainField`):** Ingestion of digital elevation models (SRTM / Copernicus) with 2D bilinear and nearest-neighbor spatial interpolation.
* **Domain Bounds Enforcement:** Strict boundary checks preventing silent extrapolation.
* **Scientific Scope:** Topographic surface relief is geometric; Phase 2 explicitly does not claim terrain-following aerodynamic flow dynamics (deferred to Phase 3).

---

## 7. OSM / Overpass Integration

* **Spatially Bounded Queries:** Bounded Overpass QL queries restricted to the simulation domain.
* **Feature Extraction:** Road network ways (`motorway`, `trunk`, `primary`, `secondary`, `tertiary`, `residential`, `service`), industrial land-use polygons (`landuse=industrial`), and industrial point features (`man_made=chimney`, `power=generator`).

---

## 8. Source Proxy Representation & Industrial Isolation

* **Road Segmentation:** Automatic subdivision of long road polylines into discrete segment source elements ($L \le 250\ \text{m}$) placed at segment midpoints.
* **Metric Length Calculation:** Road lengths calculated strictly in metric meters using conformal projected Cartesian coordinates.
* **Industrial Safety Isolation:** Industrial polygons and chimneys are preserved as geographic land-use proxies (`emission_status='unavailable'`) and are isolated from the active solver, preventing unmeasured phantom emissions.

---

## 9. Proxy-to-Emission Parameterization

* **Governing Equation:**
  $$Q_{\text{road}}(t) = L_{\text{km}} \times \left(\text{AADT}_{\text{class}} \times \frac{f(t)}{24}\right) \times \text{EF} \times \frac{1}{3600}\quad [\text{g/s}]$$
* **Diurnal Normalization:** Bimodal urban traffic profile satisfying $\frac{1}{24}\sum_{h=0}^{23} f_h = 1.0$, preserving daily mean emissions with weekend scaling (0.85).

---

## 10. Emission Factor Provenance & Scope Audit

* **Literature Provenance:** EMEP/EEA (2019) Guidebook (Tables 3-17 & 3-23) and CPCB/ARAI (2018) Indian fleet composite exhaust + brake/tyre wear database.
* **Scope:** Primary exhaust PM2.5 + non-exhaust brake wear + tyre wear in $\text{g PM2.5 / vehicle-km}$. (Resuspended road dust is excluded).
* **AADT Audit:** OSM does not provide traffic volumes; default AADT values (45k motorway down to 400 service) are engineering proxies based on IRC:106-1990 urban road design capacities, overridable by user input.
* **Road Source Initial Spread:** $\sigma_0 = (5.0, 5.0, 1.5)\ \text{m}$ grounded in EPA CALINE4 / ISC3 line/volume source initial mixing zone guidelines ($W/2.15 \approx 5.0\ \text{m}, H_{\text{wake}}/2.15 \approx 1.5\ \text{m}$).

---

## 11. Uncertainty Model

* **First-Class Classification:** Explicit assignment of `UncertaintyClass` (`LOW`, `MEDIUM`, `HIGH`).
* **Lineage Tracking:** All proxy sources carry full provenance documenting assumptions, proxy IDs, retrieval timestamps, and citations.

---

## 12. Coordinate Integration

* Unified metric Cartesian frame across meteorology, terrain grids, road segment midpoints, industrial centroids, receptors, and puff trajectories.

---

## 13. Input Assembly & Mass Conservation ($Q(t) \to M$)

* `SimulationInputAssembler.build()` produces a complete `SimulationInput` accompanied by a machine-readable JSON manifest and SHA-256 fingerprint hash.
* **Mass Conservation Verified:** Discrete puff release sum $\sum \Delta M_i = \sum Q(t_i) \Delta t_{\text{rel}}$ matches numerical time integrals $\int_0^T Q(t) dt$ and 3D spatial mass integrals.

---

## 14. Caching and Reproducibility

* Deterministic file-based JSON caching via `DataCache`.
* Offline testability with cached fixtures in `tests/fixtures/`.

---

## 15. Testing

* **Total Tests:** 179 passed, 0 failed, 0 warnings.
* **Coverage:** Open-Meteo parsing, circular wind interpolation, terrain bilinear exactness, road segmentation, dimensional scaling, $Q(t) \to M$ conservation, industrial isolation safety, provenance completeness, and end-to-end Phase 1 Puff Engine coupling.

---

## 16. Diagnostics

Generated publication-grade diagnostic figures in `sample_plots/`:
1. `phase2_meteo_timeseries.png`: Multi-panel meteorological time-series.
2. `phase2_sources_and_terrain.png`: 2D spatial map of terrain contours and classified road network segments.
3. `phase2_puff_simulation_snapshot.png`: 2D ground-level PM2.5 dispersion heatmap from multi-source traffic emissions.

---

## 17. Performance

* Input assembly for a 3 km urban domain with dozens of road segments completes in $< 0.5\ \text{s}$ offline.
* Memory footprint is bounded and vectorized.

---

## 18. Known Limitations

1. **OSM is a Proxy:** Road classifications and AADT lookups approximate traffic volumes; they are not real-time sensor measurements.
2. **Flat Wind Field:** Spatially uniform horizontal wind vector assumed during each timestep across the local domain.
3. **No Dynamic Terrain-Flow:** Terrain elevations provide surface relief but do not yet deflect wind streamlines.
4. **Passive PM2.5 Tracer:** Chemical secondary aerosol formation and dry/wet deposition are not included.

---

## 19. Scientific Assumptions

1. Primary PM2.5 is treated as an inert, non-reactive tracer.
2. Road vehicle emissions are released at ground level ($z = 0.5\ \text{m}$) with initial volume spread $\sigma_0 = (5.0, 5.0, 1.5)\ \text{m}$.
3. Ambient meteorological data from Open-Meteo represents domain-average boundary layer forcing.

---

## 20. Final Phase 2 Freeze Statement

> **Phase 2 Final Freeze Status: FROZEN & READY FOR PHASE 3**  
> *AtmosSim Phase 2 has been implemented, audited, and analytically/numerically verified across all operating scenarios. The environmental and source-data assembly pipeline transforms general geographic locations and continuous time windows into fully validated, provenance-complete, and mass-conserving inputs for the frozen Phase 1 Gaussian Puff engine. Phase 2 is frozen.*
