# AtmosSim: Physics-to-ML Atmospheric Dispersion Benchmark

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/pytest-230%20passed-brightgreen.svg)]()
[![Status](https://img.shields.io/badge/Phases%200--7-Verified%20%26%20Frozen-success.svg)]()
[![Dataset](https://img.shields.io/badge/Dataset-v1.0%20Released-orange.svg)]()

AtmosSim is a research-grade, physics-based atmospheric dispersion simulator and reproducible machine-learning benchmark framework.

---

## Overview

AtmosSim bridges physical fluid dispersion modeling and machine learning:
1. **Analytical & Lagrangian Physics Core**: Implements steady-state Gaussian Plume and time-dependent Gaussian Puff dispersion engines with Briggs dispersion parameters and Pasquill-Gifford stability.
2. **Automated Input Assembly**: Connectors for real-world Open-Meteo weather reanalysis, digital elevation terrain, and OpenStreetMap road/industrial geometries.
3. **Canonical Benchmark Dataset (v1.0)**: Factorial parameter sweep across stability, wind speed, wind direction, and emission rates, with strict zero-leakage temporal and cross-location splits.
4. **Reproducible ML Baselines**: 7 machine-learning models (Persistence, Linear, Ridge, Random Forest, XGBoost, LightGBM, CatBoost) with comprehensive regression metrics and error diagnostics.
5. **Observational Validation**: Ground-truth validation against real OpenAQ air-quality monitoring stations in Delhi NCR.

---

## Project Structure

```text
AtmosSim/
├── artifacts/
│   ├── benchmark_dataset/v1.0/        # Canonical benchmark Parquet splits & schema
│   │   ├── train.parquet
│   │   ├── validation.parquet
│   │   ├── test.parquet
│   │   ├── cross_location_test.parquet
│   │   ├── metadata.json
│   │   └── target_clipping_audit.json
│   └── ml/                            # Phase 7 ML baseline configs & metrics
│       ├── baseline_config.json
│       └── baseline_metrics.json
│
├── docs/                              # Technical documentation & audit reports
│   ├── project_verification_report.md # Master 8-gate reproducibility audit
│   ├── phase4_validation_report.md    # OpenAQ observational ground-truth report
│   ├── ml_baseline_benchmark.md       # Phase 7 ML benchmark metrics
│   ├── phase7_scientific_audit.md     # Feature-to-target scientific audit
│   ├── phase0_completion_report.md    # Phase 0 analytical plume report
│   ├── phase1_completion_report.md    # Phase 1 Lagrangian puff engine report
│   └── phase2_completion_report.md    # Phase 2 input assembly report
│
├── src/atmosim/
│   ├── physics/                       # Gaussian plume, puff engine, stability, dispersion
│   ├── data/                          # Open-Meteo, OpenAQ, Overpass, and terrain connectors
│   ├── sources/                       # Road network & industrial emission parameterization
│   ├── simulation/                    # End-to-end SimulationInputAssembler
│   ├── dataset/                       # Phase 6 benchmark dataset generation & QA
│   └── ml/                            # Phase 7 ML baselines, metrics, & evaluation
│
├── tests/                             # Full test suite (230 passed)
│   ├── test_plume.py
│   ├── test_puff.py
│   ├── test_openaq.py
│   ├── dataset/
│   └── ml/
│
├── scripts/
│   ├── generate_benchmark_dataset.py  # Dataset generator
│   ├── validate_benchmark_dataset.py  # Dataset integrity validator
│   └── run_ml_baselines.py            # Phase 7 ML training & evaluation
│
├── pyproject.toml
└── README.md
```

---

## Quickstart

### Installation
```bash
git clone https://github.com/Suraj-codes1410/AtmosSim.git
cd AtmosSim
pip install -e .
```

### Running the Test Suite
```bash
pytest -q
# Output: 230 passed
```

### Generating the Benchmark Dataset
```bash
python scripts/generate_benchmark_dataset.py
```

### Running Machine Learning Baselines
```bash
python scripts/run_ml_baselines.py
```

---

## Benchmark Results (v1.0 Dataset Release)

| Model | Test MAE ($\mu\text{g/m}^3$) | Test RMSE ($\mu\text{g/m}^3$) | Test $R^2$ | Cross-Loc RMSE ($\mu\text{g/m}^3$) | Cross-Loc $R^2$ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Persistence** | $124.51$ | $205.47$ | $-0.001$ | $221.76$ | $-0.000$ |
| **Linear Regression** | $182.74$ | $215.41$ | $-0.100$ | $178.87$ | $0.349$ |
| **Ridge Regression** | $140.21$ | $180.97$ | $0.224$ | $171.75$ | $0.400$ |
| **Random Forest** | $51.23$ | $110.99$ | $0.708$ | $117.69$ | $0.718$ |
| **XGBoost** | $53.12$ | $113.13$ | $0.697$ | $118.00$ | $0.717$ |
| **LightGBM** | $54.84$ | $117.48$ | $0.673$ | $118.45$ | $0.715$ |
| **CatBoost** | **$50.53$** | **$109.86$** | **$0.714$** | **$118.20$** | **$0.716$** |

---

## Documentation & Verification

For detailed scientific audits, sensitivity analyses, and observational validation:
- [`docs/project_verification_report.md`](docs/project_verification_report.md): Master Phase 0–7 verification report and 8-gate reproducibility audit.
- [`docs/phase4_validation_report.md`](docs/phase4_validation_report.md): OpenAQ observational validation against Delhi NCR ground monitors.
- [`docs/ml_baseline_benchmark.md`](docs/ml_baseline_benchmark.md): Detailed Phase 7 benchmark breakdown and error distributions.
