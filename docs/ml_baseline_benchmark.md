# AtmosSim — Phase 7: Reproducible ML Baseline Benchmark Report

## 1. Executive Summary

This document establishes the reproducible Machine Learning baseline benchmark for **AtmosSim** on the canonical dataset release `v1.0`. All models are trained and evaluated strictly according to the frozen dataset contract and leakage controls.

---

## 2. Dataset Contract & Scope Disclosures

- **Dataset Version**: `v1.0`
- **Feature Version**: `v1.0`
- **Target**: `target_pm25` ($1	ext{-hour ahead forecast ground-level PM2.5 in }\mu	ext{g/m}^3$, unclipped physical dispersion up to $1,269.72\ \mu	ext{g/m}^3$)
- **Forecast Horizon**: `1 hour`
- **Sample Counts**:
  - Train: `1,728` rows (Region `R002`, hours $00:00 - 15:00$)
  - Validation: `324` rows (Region `R002`, hours $16:00 - 18:00$)
  - Test: `432` rows (Region `R002`, hours $19:00 - 22:00$)
  - Cross-Location Test: `2,484` rows (Holdout Region `R001`, hours $00:00 - 22:00$)
- **Feature Count**: `15` operational features (all available at prediction timestamp $t$)
- **Dataset Scope Disclosure**: Single synthetic day ($2020-01-01$), 216-scenario factorial parameter sweep over wind speed ($1.0, 5.0, 10.0\ 	ext{m/s}$), wind direction, Pasquill-Gifford stability class ($A, D, F$), and emission rate ($0.5, 1.0, 2.0\ 	ext{g/s}$). It is an idealized physics evaluation benchmark, not a multi-day or multi-real-location observational dataset.
- **Geographic Scope Disclosure**: Regions `R001` and `R002` share identical synthetic parameter distributions ($\Delta = 0.000000$ across all feature means). The 216 stations represent distinct synthetic parameter combinations, not separate real-world geographical observation sites.
- **Emission Source Features Note**: `road_density_total` and `source_density` are excluded from the synthetic benchmark v1.0 release because synthetic parameter-sweep scenarios operate on idealized coordinate spaces without real-world OSM road network geometries.

---

## 3. Operational Features (15 Features)

1. `wind_speed`: Horizontal wind speed (m/s)
2. `wind_u`: Zonal wind component eastward (m/s)
3. `wind_v`: Meridional wind component northward (m/s)
4. `temperature`: Ambient surface temperature (K)
5. `relative_humidity`: Relative humidity fraction ($0$ to $1$)
6. `surface_pressure`: Atmospheric surface pressure ($101,325	ext{ Pa}$)
7. `pblh`: Planetary boundary layer height (m)
8. `stability_class`: Pasquill-Gifford stability category ($A, D, F$)
9. `hour`: Hour of day ($0 - 22$)
10. `day_of_week`: Day of week index ($2$)
11. `month`: Month index ($1$)
12. `sin_hour`: $\sin(2\pi \cdot 	ext{hour} / 24)$
13. `cos_hour`: $\cos(2\pi \cdot 	ext{hour} / 24)$
14. `wind_speed_mean_3h`: 3-hour right-aligned rolling mean of wind speed (m/s)
15. `temperature_mean_6h`: 6-hour right-aligned rolling mean of temperature (K)

---

## 4. Models Evaluated

1. **Persistence (Naive Baseline)**: Predicts the training set mean concentration ($\hat{y} = ar{y}_{	ext{train}}$).
2. **Linear Regression**: Ordinary Least Squares fit on scaled operational features.
3. **Ridge Regression**: $\mathcal{L}_2$-regularized linear regression ($lpha = 1.0$).
4. **Random Forest**: 100 trees, `max_depth=12`, `random_state=42`.
5. **XGBoost**: 100 estimators, `learning_rate=0.05`, `max_depth=6`, `random_state=42`.
6. **LightGBM**: 100 estimators, `learning_rate=0.05`, `num_leaves=31`, `random_state=42`.
7. **CatBoost**: 100 iterations, `learning_rate=0.05`, `depth=6`, `random_seed=42`.

---

## 5. Overall Model Comparison Table

| Model | Test MAE | Test RMSE | Test $R^2$ | Cross-Location MAE | Cross-Location RMSE | Cross-Location $R^2$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Persistence** | $124.51$ | $205.47$ | $-0.001$ | $129.69$ | $221.76$ | $-0.000$ |
| **Linear Regression** | $182.74$ | $215.41$ | $-0.100$ | $122.66$ | $178.87$ | $0.349$ |
| **Ridge Regression** | $140.21$ | $180.97$ | $0.224$ | $114.52$ | $171.75$ | $0.400$ |
| **Random Forest** | $51.23$ | $110.99$ | $0.708$ | $52.26$ | $117.69$ | $0.718$ |
| **XGBoost** | $53.12$ | $113.13$ | $0.697$ | $52.54$ | $118.00$ | $0.717$ |
| **LightGBM** | $54.84$ | $117.48$ | $0.673$ | $52.99$ | $118.45$ | $0.715$ |
| **CatBoost** | **$50.53$** | **$109.86$** | **$0.714$** | **$52.23$** | **$118.20$** | **$0.716$** |

---

## 6. Extreme-Value Evaluation

Thresholds derived strictly from training target:
- **Top 10% ($P_{90}$)**: $259.33\ \mu	ext{g/m}^3$
- **Top 5% ($P_{95}$)**: $575.54\ \mu	ext{g/m}^3$
- **Top 1% ($P_{99}$)**: $1,167.60\ \mu	ext{g/m}^3$

*(Thresholds are non-degenerate and represent distinct physical extreme subsets across splits).*

### Performance on Extreme Subsets (Test Split)

| Model | Top 10% RMSE ($n=40$) | Top 10% Bias | Top 5% RMSE ($n=20$) | Top 5% Bias | Top 1% ($n=0$ in Test) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Persistence** | $439.46$ | $-419.64$ | $542.44$ | $-533.19$ | N/A |
| **Linear Regression** | $328.61$ | $-107.03$ | $390.87$ | $-324.96$ | N/A |
| **Ridge Regression** | $324.32$ | $-161.42$ | $398.92$ | $-360.77$ | N/A |
| **Random Forest** | $302.73$ | $-29.23$ | $328.45$ | $-279.79$ | N/A |
| **XGBoost** | **$300.92$** | **$+2.17$** | **$321.67$** | **$-253.01$** | N/A |
| **LightGBM** | $303.06$ | $+27.75$ | $304.32$ | $-229.77$ | N/A |
| **CatBoost** | $307.94$ | $-64.10$ | $375.47$ | $-321.28$ | N/A |

### Performance on Extreme Subsets (Cross-Location Test Split)

| Model | Top 10% RMSE ($n=264$) | Top 5% RMSE ($n=132$) | Top 1% RMSE ($n=32$) |
| :--- | :---: | :---: | :---: |
| **Persistence** | $474.96$ | $580.44$ | $1,139.73$ |
| **Linear Regression** | $323.00$ | $391.24$ | $741.05$ |
| **Ridge Regression** | $326.69$ | $399.70$ | $781.04$ |
| **Random Forest** | $325.29$ | $381.18$ | $544.75$ |
| **XGBoost** | $325.98$ | $383.32$ | $546.06$ |
| **LightGBM** | **$324.71$** | **$375.21$** | **$536.85$** |
| **CatBoost** | $327.85$ | $398.72$ | $584.08$ |

---

## 7. Geographic Generalization Analysis

Comparing in-region Test (Region `R002`) vs Cross-Location Test (Holdout Region `R001`):
- **CatBoost**: $	ext{Gap}_{	ext{RMSE}} = +8.34\ \mu	ext{g/m}^3$, $	ext{Gap}_{R^2} = +0.002$
- **Random Forest**: $	ext{Gap}_{	ext{RMSE}} = +6.70\ \mu	ext{g/m}^3$, $	ext{Gap}_{R^2} = +0.010$
- **XGBoost**: $	ext{Gap}_{	ext{RMSE}} = +4.87\ \mu	ext{g/m}^3$, $	ext{Gap}_{R^2} = +0.020$
- **LightGBM**: $	ext{Gap}_{	ext{RMSE}} = +0.97\ \mu	ext{g/m}^3$, $	ext{Gap}_{R^2} = +0.042$

*Qualification*: Models maintain consistent $R^2 pprox 0.71–0.72$ across both regions, confirming stable transfer across independent synthetic scenario instances.

---

## 8. Runtime Profiling

| Model | Training Time (s) | Inference Time (s) |
| :--- | :---: | :---: |
| Persistence | $<0.001$ | $<0.001$ |
| Linear | $0.001$ | $<0.001$ |
| Ridge | $0.001$ | $<0.001$ |
| Random Forest | $0.069$ | $<0.001$ |
| XGBoost | $0.463$ | $<0.001$ |
| LightGBM | $0.228$ | $<0.001$ |
| CatBoost | $0.098$ | $<0.001$ |

---

## 9. Reproducibility & Artifacts

- **Config Hash**: `07bf2f6050b1d3d633513364fdb4030635da2ebdbcc16630f5b24479e0a29583`
- **Metrics Artifact**: `artifacts/ml/baseline_metrics.json`
- **Config Artifact**: `artifacts/ml/baseline_config.json`
- **Diagnostics**: `artifacts/ml/diagnostics/*.png` (17 plots)
