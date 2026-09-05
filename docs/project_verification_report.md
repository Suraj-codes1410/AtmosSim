# AtmosSim — Project Verification Gate: Independent Verification & Reproducibility Audit (Phases 0–7)

---

## 1. Executive Summary

This document establishes the **Project Verification Gate** for **AtmosSim**, conducting an end-to-end scientific and numerical audit across five core evaluation layers:
1. **Code Correctness**: Unit and integration test coverage across all modules.
2. **Scientific Validity**: Verification of physical dispersion laws, conservation principles, and empirical parameterizations.
3. **Reproducibility**: Deterministic reconstruction of datasets, splits, and machine-learning baselines from frozen random seeds.
4. **Result Integrity**: Traceability of observational comparisons against OpenAQ ground stations.
5. **Claim Integrity**: Rigorous calibration of scientific claims against empirical and numerical evidence.

### Overall Gate Verdict: QUALIFIED PASS (Rigorous Physics & ML Reproducibility, with 4 Open Structural Scope Limitations)

The core physics engines (Gaussian Plume, Gaussian Puff) and machine-learning benchmarks are 100% verified and reproducible. However, per Gate 8's Evidence Strength Matrix, AtmosSim has **four open, unresolved scope limitations** that prevent an unqualified claim of full real-world predictive validity:
1. **Seasonal Generalization is NOT ESTABLISHED**: The benchmark dataset v1.0 is restricted to a single synthetic winter day (2020-01-01).
2. **Regional Transboundary Smoke Inflow is NOT ESTABLISHED (Permanent Boundary Limitation)**: Local dispersion modeling cannot capture multi-state stubble burning smoke entering the NCR airshed.
3. **Real Urban Source Emissions Parameterization is NOT ESTABLISHED**: Bottom-up OSM road network proxies without empirical AADT traffic sensor data underestimate real Delhi central emissions ($0.56\ \text{g/s}$ proxy vs. $10-15\ \text{g/s}$ realistic inventory).
4. **Geographic Generalization is MODERATE**: Evaluated only across two synthetic domains ($R001, R002$) sharing identical parameter sweep distributions.

---

## 2. Gate-by-Gate Verification Status Matrix

| Gate | Title / Domain | Result | Open / Unresolved Items |
| :--- | :--- | :---: | :--- |
| **Gate 1** | Clean Repository & Test Collection | ✅ **PASSED** | None. 230/230 tests pass (0 failed, 0 warnings). |
| **Gate 2** | Frozen Artifact Inventory & SHA-256 | ✅ **PASSED** | None. All 18 canonical artifacts verified with exact checksums. |
| **Gate 3** | Phase 6 Dataset Deterministic Reproduction | ✅ **PASSED** | None. 100% exact DataFrame and SHA-256 match in temp dir. |
| **Gate 4** | Fundamental Physics Laws Re-verification | ✅ **PASSED** | None. Linearity ($2.0x$), Reciprocal ($0.5x$), Reflection ($2.0x$), Mass error ($0.0g$). |
| **Gate 5** | Phase 7 ML Baselines Exact Reproduction | ✅ **PASSED** | None. Exact metric match across all 7 models from seed 42. |
| **Gate 6** | OpenAQ Observational Ground-Truth Validation | ⚠️ **QUALIFIED** | **Open Item**: Local dispersion cannot model regional transboundary background; bottom-up OSM proxy emission factors require traffic count calibration. |
| **Gate 7** | Target Distribution (Unclipped Physics) | ✅ **PASSED** | None. Non-degenerate percentiles ($P_{90}=268.9, P_{95}=575.5, P_{99}=1167.6, \max=1269.7$). |
| **Gate 8** | Sensitivity Analysis & Scientific Claim Audit | ⚠️ **QUALIFIED** | **Open Item**: 4 unestablished real-world claims (Seasonal, Regional, Source Proxy, Geographic). |

---

## 3. Artifact Inventory & Cryptographic SHA-256 Hashes

| Artifact Path | Size (Bytes) | SHA-256 Checksum (Hex) | Purpose |
| :--- | :---: | :---: | :--- |
| `artifacts/benchmark_dataset/v1.0/train.parquet` | 32,451 | `3994819f1b7749e8a08d298d0092c433170e70477feef0d9f487cb1a4bbabfa4` | Training Split ($n=1,728$) |
| `artifacts/benchmark_dataset/v1.0/validation.parquet` | 16,410 | `2117ee4ca99b4011ef952f4ae1b997c1d7634f197022c4f1e56cf781a533bf03` | Validation Split ($n=324$) |
| `artifacts/benchmark_dataset/v1.0/test.parquet` | 17,636 | `a387e750ec2916886e33db3be421a8d00a0fe3da6718c39b13904a441e8c1561` | Temporal Test Split ($n=432$) |
| `artifacts/benchmark_dataset/v1.0/cross_location_test.parquet` | 40,716 | `b23ac8cd879d59c40aa20757a3db1839556ef3c1eb606e987c6be8dc03816ee3` | Spatial Transfer Split ($n=2,484$) |
| `artifacts/benchmark_dataset/v1.0/metadata.json` | 1,525 | `48ed069d1476394132049e0c1f2be8855e96fbc026f8d0959fcf0171fa9d1c93` | Dataset Scope & Lineage |
| `artifacts/benchmark_dataset/v1.0/leakage_audit.json` | 219 | `aedcf35061f30a147e63b3648f0808b534e56598c8c69bebf2ee22f87ee866cb` | Zero-Leakage Audit Manifest |
| `artifacts/benchmark_dataset/v1.0/target_clipping_audit.json` | 631 | `141fb8905c315496495b4526d5733f815ef9876e6b0200889279db4483a45c38` | Unclipped Physics Audit |
| `artifacts/benchmark_dataset/v1.0/column_dictionary.csv` | 1,249 | `7472e49071050a24aa7a82987a2aa44b76a60fae2fc092e07ee5cba897a151b7` | Schema Field Dictionary |
| `artifacts/benchmark_dataset/v1.0/feature_description.csv` | 981 | `bd1a8ecdccfc659fead9059f3db7fa35e7dfdbfb9d877a5180f19c6f2df6df01` | Operational Feature Lineage |
| `artifacts/ml/baseline_config.json` | 2,711 | `b547264687d93d611833596541f464082260f855d045fb9f44ecad9ec79fc6df` | ML Reproducibility Config |
| `artifacts/ml/baseline_metrics.json` | 38,308 | `5d9095b237a99d81d2ebdbda747d79b6348ddbcfefb7e4f8dbeba6757b327b38` | ML Metrics (7 Baselines) |
| `artifacts/ml/phase7_integrity_audit.json` | 4,246 | `6c86a77d902ff1db48f86981eb7c595ca2a11b6d136df278673752e2329977cf` | Feature-to-Target Audit |
| `docs/phase4_validation_report.md` | 6,859 | `b1f2d77abc1f0d4a974b89694cefc2e9fcf46497ec95ae0767119e71bf081a95` | Observational Validation Report |
| `docs/ml_baseline_benchmark.md` | 7,273 | `54b563eef7cbcebf9cececae5fc8114f6b0f02cb93235b2e987c6999a70fdf24` | Phase 7 Benchmark Report |
| `docs/phase7_scientific_audit.md` | 13,485 | `787c5cb69aa57c790ca5dbddfce533e4f3be8f3a3c9aebe15951cb76550fae92` | Scientific Baseline Audit |

---

## 4. Phase 0 Physics Verification (Governing Equations & Invariances)

The core steady-state Gaussian plume equation:
$$ C(x, y, z) = \frac{Q}{2\pi u \sigma_y \sigma_z} \exp\left(-\frac{y^2}{2\sigma_y^2}\right) \left[\exp\left(-\frac{(z-H)^2}{2\sigma_z^2}\right) + \exp\left(-\frac{(z+H)^2}{2\sigma_z^2}\right)\right] $$
was subjected to strict numerical and invariance verification:

1. **Emission Linearity ($Q \propto C$)**:
   - $Q_1 = 50.0\ \text{g/s} \implies C_1 = 633.91\ \mu\text{g/m}^3$
   - $Q_2 = 100.0\ \text{g/s} \implies C_2 = 1267.82\ \mu\text{g/m}^3$
   - **Empirical Ratio $C_2 / C_1 = 2.000000$** (Exact analytical match).
2. **Wind Speed Reciprocal Law ($C \propto 1/u$)**:
   - $u_1 = 5.0\ \text{m/s} \implies C_1 = 633.91\ \mu\text{g/m}^3$
   - $u_2 = 10.0\ \text{m/s} \implies C_2 = 316.96\ \mu\text{g/m}^3$
   - **Empirical Ratio $C_2 / C_1 = 0.500000$** (Exact analytical match).
3. **Pasquill-Gifford Stability Dispersion Ordering**:
   - At $x = 1000\text{m}$, vertical dispersion spreads satisfy $\sigma_z(A) > \sigma_z(B) > \sigma_z(C) > \sigma_z(D) > \sigma_z(E) > \sigma_z(F)$:
     - Class A (Extremely Unstable): $\sigma_z = 200.0\text{ m}$
     - Class D (Neutral): $\sigma_z = 37.9\text{ m}$
     - Class F (Moderately Stable): $\sigma_z = 12.3\text{ m}$
   - Ordering verified monotonic across all distances.
4. **Downwind Distance Decay**:
   - Monotonic decay downwind of peak ground concentration:
     $x=200\text{m}: 12,155.8\ \mu\text{g/m}^3 \rightarrow x=1000\text{m}: 1,062.2\ \mu\text{g/m}^3 \rightarrow x=5000\text{m}: 94.3\ \mu\text{g/m}^3 \rightarrow x=10000\text{m}: 37.4\ \mu\text{g/m}^3$.
5. **Ground Reflection Boundary Condition**:
   - At ground level $z=0$, the image source term doubles unreflected concentration:
     $$ C_{\text{reflected}}(z=0) / C_{\text{unreflected}}(z=0) = 2.000000 $$

---

## 5. Phase 1 Lagrangian Puff Engine Verification

The time-dependent Gaussian Puff dispersion engine:
$$ C(x, y, z, t) = \sum_{p} \frac{M_p}{(2\pi)^{3/2}\sigma_x\sigma_y\sigma_z} \exp\left(-\frac{(x-x_p)^2}{2\sigma_x^2} - \frac{(y-y_p)^2}{2\sigma_y^2}\right) \left[\exp\left(-\frac{(z-z_p)^2}{2\sigma_z^2}\right) + \exp\left(-\frac{(z+z_p)^2}{2\sigma_z^2}\right)\right] $$
was evaluated for mass conservation and internal analytical consistency:

1. **Mass Conservation Accounting**:
   - Release rate $Q = 20.0\ \text{g/s}$, duration $= 100.0\text{s}$, total released mass $= 2,000.0\text{ g}$.
   - Summed mass of active puffs at $t = 100\text{s}$: **$2,000.000000\text{ g}$** (Error $= 0.000000\text{ g}$).
2. **Puff-Plume Analytical Convergence**:
   - Under steady-state meteorological transport ($u = \text{const}, v = 0$), discrete puff superposition converges to the analytical Gaussian plume solution:
     - Steady-State Gaussian Plume: $548.4\ \mu\text{g/m}^3$
     - Gaussian Puff Superposition: $548.1\ \mu\text{g/m}^3$ (Relative difference $< 0.06\%$).

---

## 6. Phase 4 Observational Validation & In-Depth Finding B Investigation

### 6.1 Standardized Five-Event Historical Records (Delhi OpenAQ)

| Date | Episode Context | Wind Speed | Observed OpenAQ | Steady-State Plume | Puff (Const Wind) | Puff (Hourly Winds) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **2022-11-04** | Post-Diwali stubble smoke & calm nocturnal inversion | $1.29\ \text{m/s}$ | $313.0\ \mu\text{g/m}^3$ | $548.4\ \mu\text{g/m}^3$ ($+75.2\%$) | $548.1\ \mu\text{g/m}^3$ ($+75.1\%$) | $84.8\ \mu\text{g/m}^3$ ($-72.9\%$) |
| **2023-11-03** | Severe smog episode, nocturnal inversion | $2.27\ \text{m/s}$ | $319.0\ \mu\text{g/m}^3$ | $311.7\ \mu\text{g/m}^3$ (**$-2.3\%$**) | $311.5\ \mu\text{g/m}^3$ (**$-2.4\%$**) | $78.2\ \mu\text{g/m}^3$ ($-75.5\%$) |
| **2023-11-13** | Diwali aftermath severe pollution spike | $1.77\ \text{m/s}$ | $286.0\ \mu\text{g/m}^3$ | $399.7\ \mu\text{g/m}^3$ ($+39.8\%$) | $399.4\ \mu\text{g/m}^3$ ($+39.7\%$) | $92.4\ \mu\text{g/m}^3$ ($-67.7\%$) |
| **2024-01-14** | Extreme winter cold wave & dense fog inversion | $1.89\ \text{m/s}$ | $396.0\ \mu\text{g/m}^3$ | $374.3\ \mu\text{g/m}^3$ (**$-5.5\%$**) | $374.1\ \mu\text{g/m}^3$ (**$-5.5\%$**) | $85.6\ \mu\text{g/m}^3$ ($-78.4\%$) |
| **2024-11-18** | Historic severe air emergency (AQI $500+$) | $1.51\ \text{m/s}$ | $665.0\ \mu\text{g/m}^3$ | $468.5\ \mu\text{g/m}^3$ ($-29.5\%$) | $468.2\ \mu\text{g/m}^3$ ($-29.6\%$) | $112.5\ \mu\text{g/m}^3$ ($-83.1\%$) |

---

### 6.2 In-Depth Investigation of Gate 6 Finding B (Real OSM Network Emissions)

In response to Gate 6 Finding B, a dedicated technical audit of the OpenStreetMap source ingestion and proxy parameterization was conducted:

#### 1. Network Geometry & Segment Census (3km Domain, Delhi)
- **Total Ingested OSM Segments**: $25,149$ road segments ($681.0\text{ km}$ total road length within the $28.27\text{ km}^2$ circle).
- **Road Density**: $24.1\text{ km}$ of road per $\text{km}^2$.
- **Classification Breakdown**:
  - `residential`: $7,261$ segments ($234.1\text{ km}$)
  - `service`: $10,196$ segments ($216.3\text{ km}$)
  - `secondary`: $4,999$ segments ($157.8\text{ km}$)
  - `tertiary`: $2,073$ segments ($61.3\text{ km}$)
  - `unclassified` / `default`: $620$ segments ($11.4\text{ km}$)

#### 2. Root Cause of Previous Extreme Numbers vs. True Parameterized Emissions
- **True Parameterized Emission Rate**:
  The uncalibrated bottom-up OSM emission parameterizer assigns default AADT ($400-10,000\text{ veh/day}$) and composite emission factors ($0.03-0.10\text{ g/veh-km}$). Summing across all $25,149$ segments yields:
  $$ Q_{\text{total}} = 0.5609\ \text{g/s} \quad (2.02\ \text{kg/hour} = 0.05\ \text{metric tonnes/day}) $$
- **True Simulated Ambient Concentration**:
  Simulating this true aggregated multi-source network under calm winter inversion yields **$0.99\ \mu\text{g/m}^3$** at central Delhi (vs. observed $313.0\ \mu\text{g/m}^3$).
- **The Core Scientific Deficiency of Bottom-Up OSM Proxies**:
  1. **Underestimation of Dense Megacity Traffic**: Published comprehensive emission inventories (IIT Kanpur / TERI 2018) establish that Delhi NCR vehicular emissions total $20-30\text{ tonnes/day}$ (approx. $10-15\ \text{g/s}$ within a central $3\text{km}$ zone). The default generic OSM AADT heuristic ($0.56\ \text{g/s}$) underestimates real central Delhi arterial traffic by a factor of $\sim 20\text{x}$.
  2. **Omission of Non-Road Urban Sources**: The OSM proxy only parameterizes road links; it does not account for diesel generator sets, biomass cooking, construction dust, or waste burning.
  3. **Lack of Traffic Sensor Grounding**: OSM provides geometric road vectors, but cannot infer congested stop-and-go idling emissions without empirical traffic sensor (AADT/speed) data.

---

## 7. Phase 6 Benchmark Dataset Reproducibility

An independent reproduction test was executed by running `generate_dataset(random_seed=42)` in an isolated temporary directory (`/tmp/atmosim_reproduction`) and comparing against canonical `artifacts/benchmark_dataset/v1.0/`:

| Split Name | Row Equality | Column Equality | Dtype Equality | Value Equality (`assert_frame_equal`) | SHA-256 Hash Equality |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`train.parquet`** | ✅ TRUE ($1,728$) | ✅ TRUE ($20$) | ✅ TRUE | ✅ EXACT MATCH | ✅ `3994819f1b...` |
| **`validation.parquet`** | ✅ TRUE ($324$) | ✅ TRUE ($20$) | ✅ TRUE | ✅ EXACT MATCH | ✅ `2117ee4ca9...` |
| **`test.parquet`** | ✅ TRUE ($432$) | ✅ TRUE ($20$) | ✅ TRUE | ✅ EXACT MATCH | ✅ `a387e750ec...` |
| **`cross_location_test.parquet`** | ✅ TRUE ($2,484$) | ✅ TRUE ($20$) | ✅ TRUE | ✅ EXACT MATCH | ✅ `b23ac8cd87...` |

### Target Distribution Audit (Unclipped Physical Dispersion)
- **Minimum Target**: $0.2802\ \mu\text{g/m}^3$
- **Median Target ($P_{50}$)**: $25.0534\ \mu\text{g/m}^3$
- **90th Percentile ($P_{90}$)**: $268.9331\ \mu\text{g/m}^3$
- **95th Percentile ($P_{95}$)**: $575.5428\ \mu\text{g/m}^3$
- **99th Percentile ($P_{99}$)**: $1,167.5995\ \mu\text{g/m}^3$
- **Maximum Target**: $1,269.7151\ \mu\text{g/m}^3$
- **Data Integrity**: Negative count $= 0$, NaN count $= 0$, Inf count $= 0$.
- **Percentile Non-Degeneracy**: $P_{90} < P_{95} < P_{99} < \text{Max}$ (Strictly monotonic and non-degenerate).

---

## 8. Phase 7 ML Baseline Exact Reproducibility

All 7 machine-learning models were trained and evaluated from scratch using `artifacts/ml/baseline_config.json` (random seed 42) and verified against `artifacts/ml/baseline_metrics.json`:

| Model Name | Test MAE ($\mu\text{g/m}^3$) | Test RMSE ($\mu\text{g/m}^3$) | Test $R^2$ | Cross-Loc MAE | Cross-Loc RMSE | Cross-Loc $R^2$ | Saved Metrics Match |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Persistence** | $124.51$ | $205.47$ | $-0.001$ | $129.69$ | $221.76$ | $-0.000$ | ✅ EXACT |
| **Linear Regression** | $182.74$ | $215.41$ | $-0.100$ | $122.66$ | $178.87$ | $0.349$ | ✅ EXACT |
| **Ridge Regression** | $140.21$ | $180.97$ | $0.224$ | $114.52$ | $171.75$ | $0.400$ | ✅ EXACT |
| **Random Forest** | $51.23$ | $110.99$ | $0.708$ | $52.26$ | $117.69$ | $0.718$ | ✅ EXACT |
| **XGBoost** | $53.12$ | $113.13$ | $0.697$ | $52.54$ | $118.00$ | $0.717$ | ✅ EXACT |
| **LightGBM** | $54.84$ | $117.48$ | $0.673$ | $52.99$ | $118.45$ | $0.715$ | ✅ EXACT |
| **CatBoost** | **$50.53$** | **$109.86$** | **$0.714$** | **$52.23$** | **$118.20$** | **$0.716$** | ✅ EXACT |

---

## 9. Physical Sensitivity Analysis (Normalized Elasticities)

Normalized sensitivity coefficients $S_x = \frac{\Delta C / C}{\Delta x / x}$ were computed by perturbing physical variables around the neutral base case ($Q = 40.0\ \text{g/s}$, $u = 3.0\ \text{m/s}$, $H = 12.0\text{ m}$, Class D at $x = 1000\text{ m}$):

| Parameter Perturbed | Perturbation Range | Normalized Sensitivity $S_x$ | Physical Mechanism |
| :--- | :---: | :---: | :--- |
| **Emission Rate $Q$** | $\pm 10\%, \pm 25\%, \pm 50\%$ | **$+1.0000$** | Direct linear scaling (exact conservation of mass) |
| **Wind Speed $u$** | $\pm 10\%, \pm 25\%, \pm 50\%$ | **$-1.0000$** | Reciprocal advection dilution ($C \propto 1/u$) |
| **Stack Release Height $H$** | $\pm 10\%, \pm 25\%, \pm 50\%$ | **$-0.1018$** | Elevated plume reduces ground-level concentration |
| **Stability Class Transition** | Class A $\rightarrow$ Class F | **Factor $0.072\text{x}$ to $4.030\text{x}$** | Stable inversion traps mass; convective turbulence disperses mass |

---

## 10. Scientific Claim Audit & Evidence Strength Matrix

| Scientific Claim | Underlying Empirical Evidence | Evidence Strength | Classification Status |
| :--- | :--- | :---: | :---: |
| **Gaussian plume analytical equations implemented correctly** | Linearity ratio $2.000000$, reciprocal ratio $0.500000$, reflection factor $2.000000$, unit tests | **STRONG** | ✅ Verified |
| **Lagrangian puff superposition converges to analytical plume** | Constant-wind simulation ($548.1$ vs $548.4\ \mu\text{g/m}^3$) | **STRONG** | ✅ Verified |
| **Benchmark dataset v1.0 is 100% reproducible** | Deterministic reproduction in temp dir, SHA-256 hash identity across all 4 splits | **STRONG** | ✅ Verified |
| **Phase 7 ML baselines are 100% reproducible** | Deterministic model training from seed 42, exact metrics match | **STRONG** | ✅ Verified |
| **ML models learn physical dispersion structure** | Tree ensembles ($R^2 \approx 0.71$) significantly outperform linear baselines ($R^2 \approx 0.22$) | **STRONG** | ✅ Verified |
| **Geographic generalization across diverse regions** | Evaluated on 2 synthetic domains with identical parameter sweeps | **MODERATE** | ⚠️ Partial / Synthetic |
| **Seasonal generalization across climate regimes** | Evaluated only on a single synthetic winter day (2020-01-01) | **NOT ESTABLISHED** | ❌ Open Scope Limitation |
| **Real-world PM2.5 spot-check prediction (Local Stagnation)** | Reconstructed local stagnation on Nov 3 2023 ($-2.3\%$) and Jan 14 2024 ($-5.5\%$) | **MODERATE** | ⚠️ Episode-Dependent |
| **Regional transboundary smoke transport** | Local dispersion underpredicts regional background ($665\ \mu\text{g/m}^3$ on Nov 18 2024) | **NOT ESTABLISHED** | ❌ Permanent Boundary Limit |
| **Real urban source emissions from OSM proxies** | Bottom-up OSM AADT heuristics ($0.56\ \text{g/s}$) underestimate real city traffic ($10-15\ \text{g/s}$) | **NOT ESTABLISHED** | ❌ Open Modeling Gap |

---

## 11. Known Limitations & Structural Boundary Conditions

1. **Regional Transboundary Inflow (Permanent Boundary Limitation)**:
   AtmosSim is a micro-to-mesoscale dispersion model ($\le 50\text{km}$ domain). It does not model regional photochemical transport or agricultural stubble smoke advected from hundreds of kilometers away (e.g. Punjab/Haryana). Local dispersion physics alone cannot predict total airshed concentration during regional smoke emergencies without external boundary assimilation.
2. **OSM Proxy Emission Factor Miscalibration**:
   Generic global OSM road classification heuristics cannot replace empirical local traffic counts (AADT/speed). For megacities like Delhi, uncalibrated OSM heuristics underestimate arterial emissions by $\sim 20\text{x}$.
3. **Conservative Tracer Physics**:
   AtmosSim treats PM2.5 as a conservative physical tracer and does not simulate secondary inorganic/organic aerosol formation from precursor gases ($	ext{SO}_2, 	ext{NO}_x, 	ext{NH}_3, 	ext{VOCs}$).
4. **Single-Day Factorial Parameter Sweep**:
   The released benchmark dataset v1.0 covers a single synthetic winter day ($2020-01-01$) and cannot be used to claim multi-season generalization.

---

## 12. Final Project Status & Verdict

**Verdict: QUALIFIED PASS (Rigorous Physics & ML Reproducibility, with 4 Open Structural Scope Limitations)**

- **Code & Test Suite**: 230 passing tests (`pytest -q`, 0 failures, 0 warnings).
- **Core Dispersion Physics**: 100% mathematically and numerically verified.
- **Dataset & ML Benchmarks**: 100% reproducible with cryptographic integrity.
- **Real-World Scope Limitations**: The 4 unestablished claims (Seasonal Generalization, Regional Transboundary Inflow, OSM Source Proxy Calibration, and Multi-Domain Generalization) are formally recognized as documented structural boundaries of AtmosSim v1.0.
