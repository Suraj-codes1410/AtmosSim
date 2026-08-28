# AtmosSim: Physics-to-ML Atmospheric Dispersion Benchmark

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/pytest-155%20passed-brightgreen.svg)]()
[![Status](https://img.shields.io/badge/Phase%201-Complete-success.svg)]()

AtmosSim is a research-grade, physics-based atmospheric dispersion simulator and machine learning benchmark framework.

---

## Current Status: Phase 1 Complete

* **Phase 0 — Physics Foundation & Gaussian Plume Baseline:** Verified analytical steady-state plume solver, PGT stability classification, and Briggs rural/urban dispersion parameterizations ([`docs/physics_references.md`](docs/physics_references.md)).
* **Phase 1 — Time-Dependent Gaussian Puff Engine:** Fully verified Lagrangian puff advection under variable wind fields, multi-source emission schedules, dynamic dispersion growth ($\sigma_x = \sigma_y$), automated lifecycle culling, memory boundedness, and geodetic coordinate transformations ([`docs/phase1_physics_references.md`](docs/phase1_physics_references.md)).

---

## Project Structure

```text
AtmosSim/
├── docs/
│   ├── physics_references.md          # Phase 0 physical foundation & plume references
│   ├── physics_parameterization_audit.md # Parameter audit & traceability matrix
│   ├── phase0_completion_report.md    # Phase 0 completion report
│   ├── phase1_physics_references.md   # Phase 1 Gaussian Puff physics & sigma_x provenance
│   └── phase1_completion_report.md    # Phase 1 completion & verification report
│
├── src/
│   └── atmosim/
│       ├── __init__.py
│       ├── physics/
│       │   ├── __init__.py
│       │   ├── stability.py           # Pasquill-Gifford-Turner stability classification
│       │   ├── dispersion.py          # Briggs (1973/1974) dispersion parameterizations
│       │   ├── plume.py               # Analytical Gaussian Plume solver
│       │   ├── coordinates.py         # WGS84 to local metric Cartesian projection
│       │   ├── puff_lifecycle.py      # Puff lifecycle states and culling policies
│       │   └── puff.py                # Time-dependent Gaussian Puff Engine
│       │
│       └── visualization/
│           ├── __init__.py
│           ├── plume.py               # Plume diagnostic plotting utilities
│           └── puff.py                # Puff diagnostic plotting utilities
│
├── tests/
│   ├── __init__.py
│   ├── test_stability.py              # Stability classification unit tests
│   ├── test_dispersion.py             # Dispersion coefficient unit tests
│   ├── test_plume.py                  # Plume physics, scaling, mass flux & reference cases
│   ├── test_coordinates.py            # Coordinate projection & round-trip tests
│   ├── test_puff_lifecycle.py         # Lifecycle culling & memory boundedness tests
│   ├── test_puff_stability.py         # Puff dispersion growth across stability classes
│   └── test_puff.py                  # Puff advection, wind reversal, 3D conservation
│
├── scripts/
│   ├── generate_plume_diagnostics.py  # Phase 0 diagnostic plot generation
│   └── generate_puff_diagnostics.py   # Phase 1 diagnostic plot generation
│
├── sample_plots/                      # Generated diagnostic figures
│   ├── gaussian_plume_baseline.png
│   ├── stability_comparison.png
│   ├── wind_comparison.png
│   ├── emission_comparison.png
│   ├── crosswind_slice.png
│   ├── downwind_centerline.png
│   ├── puff_single_constant_wind.png
│   ├── puff_rotating_wind.png
│   ├── puff_wind_reversal.png
│   ├── puff_stability_growth.png
│   ├── puff_multi_source.png
│   └── puff_lifecycle_memory.png
│
├── pyproject.toml
└── README.md
```

---

## Quickstart & Verification

### Running the Test Suite
```bash
pytest -v
```

### Generating Diagnostic Visualizations
```bash
# Phase 0 Gaussian Plume Diagnostics
python scripts/generate_plume_diagnostics.py

# Phase 1 Gaussian Puff Diagnostics
python scripts/generate_puff_diagnostics.py
```

---

## Next Steps: Phase 2
Phase 2 will integrate **Real Terrain & Geographic Data Ingestion** (Digital Elevation Models, terrain-following advection, and land-use roughness mapping).
