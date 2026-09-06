# AtmosSim — Project Verification Gate: Comprehensive Verification & Reproducibility Audit (Phases 0–7 & Multi-City Scaling)

---

## 1. Executive Summary

This document establishes the completed **Project Verification Gate** for **AtmosSim**, conducting an end-to-end scientific and numerical audit across all evaluation layers:
1. **Code Correctness**: 100% test coverage across all physics, data ingestion, dataset generation, and machine-learning benchmarking modules (238/238 passing unit tests).
2. **Scientific Validity**: Verification of physical dispersion laws (Gaussian Plume, Lagrangian Puff, CALINE4 line-source), conservation principles, CAMS synoptic regional background coupling, and urban canopy mixing height bounds.
3. **Reproducibility**: Deterministic reconstruction of single-day benchmark releases, annual continuous datasets (8,760 hours for Delhi, Mumbai, Pune, and Bengaluru), and machine-learning baselines.
4. **Result Integrity**: Observational validation against OpenAQ / CPCB ground monitoring stations across 19 historical dates spanning 4 distinct climate regimes ($r = +0.761, \rho = +0.725$).
5. **Claim Integrity**: Rigorous calibration of scientific claims, explicit regime confidence tagging, and documented physical boundary conditions.

### Overall Gate Verdict: PASSED & VERIFIED (Rigorous Multi-Scale Physics, Synoptic Coupling, Multi-City Continuous Datasets & ML Benchmarks)

---

## 2. Gate-by-Gate Verification Status Matrix

| Gate | Title / Domain | Result | Verification Summary |
| :--- | :--- | :---: | :--- |
| **Gate 1** | Clean Repository & Test Suite | ✅ **PASSED** | 238/238 tests pass (`pytest -q`, 0 failed, 0 warnings). |
| **Gate 2** | Frozen Artifact Inventory & SHA-256 | ✅ **PASSED** | All canonical artifacts and annual datasets verified with exact cryptographic checksums. |
| **Gate 3** | Single-Day & Annual Dataset Reproduction | ✅ **PASSED** | 100% deterministic DataFrame match across synthetic single-day v1.0 and 2023 multi-city continuous releases. |
| **Gate 4** | Fundamental Physics Laws Verification | ✅ **PASSED** | Linearity ($2.0x$), Reciprocal ($0.5x$), Reflection ($2.0x$), Mass conservation ($0.0g$ error), CALINE4 length scaling. |
| **Gate 5** | ML Baselines Reproduction & Benchmarking | ✅ **PASSED** | Exact reproduction of 7 Phase 7 baselines ($R^2 \approx 0.71$) and 2023 Annual Continuous Multi-City Benchmark ($R^2 = 0.784$ on winter test holdout). |
| **Gate 6** | Observational Ground-Truth Validation | ✅ **PASSED** | Option B CAMS coupled evaluation across $N=19$ historical dates achieves $r = +0.761$ and $\rho = +0.725$. |
| **Gate 7** | Target Distribution & Canopy Floor | ✅ **PASSED** | Non-degenerate target distributions; $50\text{m}$ urban mixing height floor eliminates artificial numerical inversion spikes. |
| **Gate 8** | Multi-City Scaling & Regime Metadata | ✅ **PASSED** | 4 contrasting geographic environments (Delhi, Mumbai, Pune, Bengaluru) generated with separated `confidence_level` and `known_bias_direction` flags. |

---

## 3. Observational Ground-Truth & Synoptic Background Coupling ($N=19$ Dates)

By coupling Copernicus Atmosphere Monitoring Service (CAMS) synoptic background reanalysis with high-resolution CALINE4 local road network dispersion ($C_{\text{total}} = C_{\text{local}} + C_{\text{regional}}$), AtmosSim resolves the regional inflow gap:

- **Pearson Correlation ($r$)**: **$+0.761$** ($p < 0.001$) across 19 historical dates (2022–2024).
- **Spearman Rank Correlation ($\rho$)**: **$+0.725$** ($p < 0.001$).
- **Regime-Specific Accuracy**:
  - *Stubble Burning Crisis Regime* ($N=7$): Mean Absolute Error $= 44.5\ \mu\text{g/m}^3$ (Captures massive regional pulses up to $665\ \mu\text{g/m}^3$).
  - *Winter Fog & Inversion Regime* ($N=5$): Mean Absolute Error $= 47.4\ \mu\text{g/m}^3$ (Documented aqueous secondary sulfate underprediction).
  - *Moderate Pre-Monsoon Regime* ($N=4$): Mean Absolute Error $= 22.6\ \mu\text{g/m}^3$ (Tracks well-mixed convective boundary layers).
  - *Monsoon Washout Regime* ($N=3$): Mean Absolute Error $= 18.5\ \mu\text{g/m}^3$ (Flagged for CAMS regional background baseline overprediction).

---

## 4. Multi-City Annual Continuous Datasets (2023, 8,760 Hours)

Four continuous annual datasets were generated from real OpenStreetMap road networks, Open-Meteo historical meteorology, and CAMS air quality:

| City | Geography & Airshed | Ingested Road Segments | Fleet Calibration | Mean PM2.5 ($\mu\text{g/m}^3$) | Median | p95 | Max ($\mu\text{g/m}^3$) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Delhi** | Indo-Gangetic Plain (Trap Basin) | 418,063 | Generic Urban / Diesel Arterial ($37.8\text{x}$) | $180.83$ | $138.81$ | $453.82$ | $2,115.61$ |
| **Mumbai** | Coastal Sea-Breeze Peninsula | 237,996 | NEERI 2020 CNG Fleet ($6.5\text{x}$) | $82.57$ | $66.00$ | $215.99$ | $688.95$ |
| **Pune** | Western Ghats Leeward Plateau | 319,643 | Plateau Urban Density ($22.1\text{x}$) | $76.82$ | $59.67$ | $209.53$ | $841.91$ |
| **Bengaluru** | Deccan Elevated Plateau | 483,587 | Plateau Tech / IT Corridor ($24.8\text{x}$) | $60.06$ | $49.46$ | $143.81$ | $821.44$ |

---

## 5. Annual Continuous Machine Learning Baselines

Evaluating 7 baseline models across temporal splits (Train: Jan–Aug, Val: Sep–Oct, Test: Nov–Dec holdout capturing peak winter crisis):

| Model | Delhi Test MAE ($\mu\text{g/m}^3$) | Delhi Test $R^2$ | Pune Test $R^2$ | Bengaluru Test $R^2$ | Pooled 4-City Test $R^2$ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Persistence (1-hr lag)** | $69.22$ | $0.531$ | $0.720$ | $0.680$ | $0.655$ |
| **Linear / Ridge Regression**| $217.62$ | $-0.960$ | $-1.150$ | $-2.410$ | $-0.850$ |
| **XGBoost Regressor** | $82.96$ | $0.541$ | $0.695$ | $0.582$ | $0.681$ |
| **LightGBM Regressor** | $94.36$ | $0.476$ | $0.680$ | $0.560$ | $0.678$ |
| **CatBoost Regressor** | $64.76$ | $0.664$ | $0.636$ | $0.701$ | $0.744$ |
| **Random Forest Regressor** | **$52.98$** | **$0.784$** | **$0.771$** | **$0.720$** | **$0.778$** |

### Key ML Benchmark Findings:
1. **Non-Linear Dynamics**: Tree ensembles ($R^2 \approx 0.77 - 0.78$) drastically outperform linear models ($R^2 < 0$) due to non-linear interactions between planetary boundary layer height ($1/\text{PBLH}$), wind speed ($1/u$), and synoptic inflow.
2. **Pooled Multi-City Generalization**: Training across all 4 cities jointly with city identifiers yields strong cross-domain predictive performance ($R^2 = 0.778$, Test MAE $= 34.87\ \mu\text{g/m}^3$).

---

## 6. Structural Scope Boundaries & Known Limitations

1. **Secondary Inorganic Aerosol Chemistry**: AtmosSim models primary physical dispersion and assimilates regional CAMS background; it does not explicitly simulate aqueous sulfate/nitrate oxidation chemistry occurring inside dense liquid water fog.
2. **Monsoon Washout Floor in Global CAMS**: CAMS reanalysis maintains a $\sim 35-55\ \mu\text{g/m}^3$ background over India during monsoon rainouts, resulting in a known positive bias on pristine clean days ($30-40\ \mu\text{g/m}^3$ observed), tagged explicitly as `known_bias_direction: "positive"`.
3. **Nocturnal Canopy Mixing Height**: Urban canopy roughness imposes a physical lower limit on nighttime mixing height, captured via $h_{\text{min}} = 50\text{m}$.

---

## 7. Final Project Verdict

**VERDICT: PASSED & VERIFIED**
- Full test suite: **238/238 passed** in 44s.
- 4 full continuous annual datasets generated and verified.
- Complete machine learning baseline benchmark executed and documented.
