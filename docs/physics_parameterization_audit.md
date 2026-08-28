# AtmosSim — Phase 0 Scientific Parameterization Audit & Traceability Matrix

## 1. Audit Overview & Objectives

This audit verifies the exact mathematical provenance, parameter coefficients, distance units, valid empirical domains, and implementation-to-test traceability for every physical component in AtmosSim Phase 0.

### Evidence Level Framework
To ensure scientific integrity, all components in AtmosSim are classified according to five standardized evidence levels:
* **Level 1 — Implemented:** Python source code exists and executes without runtime errors.
* **Level 2 — Unit Tested:** Software unit tests pass assertions under standard execution.
* **Level 3 — Analytically Verified:** The implementation exactly reproduces closed-form mathematical derivations, symmetry invariants, scaling laws, and numerical conservation relationships.
* **Level 4 — Literature Reproduced:** The implementation reproduces a published worked example or documented reference result from an authoritative source.
* **Level 5 — Observationally Validated:** The model predictions have been evaluated and validated against real-world physical sensor observations (e.g. CAAQMS monitoring networks, tracer gas field trials).

**Phase 0 Status:** Establishes **Levels 1, 2, and 3** across all core modules, with published equation grounding (**Level 4 equation provenance**). Real-world observational validation (**Level 5**) is scheduled for **Phase 4**.

---

## 2. Atmospheric Stability Parameterization Audit

* **Source Framework:** Pasquill (1961), Gifford (1961), Turner (1964), U.S. EPA ISC3 (1995), EPA SRDT Guidance (1999).
* **Implementation:** [`src/atmosim/physics/stability.py`](../src/atmosim/physics/stability.py)
* **Unit Test File:** [`tests/test_stability.py`](../tests/test_stability.py)

### Parameterization Audit Table

| Parameter / Regime | Input Condition | Stability Class | Primary Source | Source Identifier | Evidence Level | Verification Test |
| :--- | :--- | :---: | :--- | :--- | :---: | :--- |
| **Daytime Strong Insolation** | $R_s > 600\ \text{W/m}^2$ or $\theta_{\text{elev}} > 60^\circ$, $u < 3\ \text{m/s}$ | **A** | Pasquill (1961) / Turner (1964) | Met. Mag. 90, Table 1 | Level 3 | `test_daytime_strong_insolation` |
| **Daytime Strong Insolation** | $R_s > 600\ \text{W/m}^2$, $3 \le u < 5\ \text{m/s}$ | **B** | Pasquill (1961) / Turner (1964) | Met. Mag. 90, Table 1 | Level 3 | `test_daytime_strong_insolation` |
| **Daytime Strong Insolation** | $R_s > 600\ \text{W/m}^2$, $u \ge 5\ \text{m/s}$ | **C** | Pasquill (1961) / Turner (1964) | Met. Mag. 90, Table 1 | Level 3 | `test_daytime_strong_insolation` |
| **Daytime Moderate Insolation** | $300 \le R_s \le 600\ \text{W/m}^2$, $u < 3\ \text{m/s}$ | **B** | Turner (1964) / EPA ISC3 (1995) | J. Appl. Met. 3(1), Table 1 | Level 3 | `test_daytime_moderate_insolation` |
| **Daytime Moderate Insolation** | $300 \le R_s \le 600\ \text{W/m}^2$, $3 \le u < 6\ \text{m/s}$ | **C** | Turner (1964) / EPA ISC3 (1995) | J. Appl. Met. 3(1), Table 1 | Level 3 | `test_daytime_moderate_insolation` |
| **Daytime Moderate Insolation** | $300 \le R_s \le 600\ \text{W/m}^2$, $u \ge 6\ \text{m/s}$ | **D** | Turner (1964) / EPA ISC3 (1995) | J. Appl. Met. 3(1), Table 1 | Level 3 | `test_daytime_moderate_insolation` |
| **Daytime Slight Insolation** | $0 < R_s < 300\ \text{W/m}^2$, $u < 2\ \text{m/s}$ | **B** | Pasquill (1961) / Turner (1964) | Met. Mag. 90, Table 1 | Level 3 | `test_daytime_slight_insolation` |
| **Daytime Slight Insolation** | $0 < R_s < 300\ \text{W/m}^2$, $2 \le u < 5\ \text{m/s}$ | **C** | Pasquill (1961) / Turner (1964) | Met. Mag. 90, Table 1 | Level 3 | `test_daytime_slight_insolation` |
| **Daytime Slight Insolation** | $0 < R_s < 300\ \text{W/m}^2$, $u \ge 5\ \text{m/s}$ | **D** | Pasquill (1961) / Turner (1964) | Met. Mag. 90, Table 1 | Level 3 | `test_daytime_slight_insolation` |
| **Nighttime Cloudy** | $f_{\text{cloud}} \ge 0.5$, $u < 3\ \text{m/s}$ | **E** | Pasquill (1961) / EPA ISC3 (1995) | EPA-454/B-95-003b | Level 3 | `test_nighttime_cloudy` |
| **Nighttime Cloudy** | $f_{\text{cloud}} \ge 0.5$, $u \ge 3\ \text{m/s}$ | **D** | Pasquill (1961) / EPA ISC3 (1995) | EPA-454/B-95-003b | Level 3 | `test_nighttime_cloudy` |
| **Nighttime Clear** | $f_{\text{cloud}} < 0.5$, $u < 3\ \text{m/s}$ | **F** | Pasquill (1961) / EPA ISC3 (1995) | EPA-454/B-95-003b | Level 3 | `test_nighttime_clear` |
| **Nighttime Clear** | $f_{\text{cloud}} < 0.5$, $3 \le u < 5\ \text{m/s}$ | **E** | Pasquill (1961) / EPA ISC3 (1995) | EPA-454/B-95-003b | Level 3 | `test_nighttime_clear` |
| **Nighttime Clear** | $f_{\text{cloud}} < 0.5$, $u \ge 5\ \text{m/s}$ | **D** | Pasquill (1961) / EPA ISC3 (1995) | EPA-454/B-95-003b | Level 3 | `test_nighttime_clear` |
| **Overcast Invariant** | $f_{\text{cloud}} \ge 0.875$ ($\ge 7/8$ octas), day or night | **D** | Turner (1964) / EPA ISC3 (1995) | EPA-454/B-95-003b | Level 3 | `test_overcast_always_neutral` |

---

## 3. Briggs Dispersion Parameterization Audit

* **Source Framework:** Briggs (1973), Briggs (1974), Gifford (1976), U.S. EPA ISC3 (1995, Section 1.1.2).
* **Implementation:** [`src/atmosim/physics/dispersion.py`](../src/atmosim/physics/dispersion.py)
* **Unit Test File:** [`tests/test_dispersion.py`](../tests/test_dispersion.py)
* **Distance Contract:** $x$ in meters ($\text{m}$), returning $\sigma_y, \sigma_z$ in meters ($\text{m}$).
* **Valid Empirical Domain:** $100\ \text{m} \le x \le 10,000\ \text{m}$ ($0.1\ \text{km} \le x \le 10\ \text{km}$).

### Rural Dispersion Formulas Audit (Briggs, 1973, Table 1)

| Class | Regime | Parameter | Exact Analytical Formula | Distance Units | Output Units | Valid Range | Source Reference |
| :---: | :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| **A** | Rural | $\sigma_y(x)$ | $\sigma_y = \frac{0.22 x}{\sqrt{1 + 0.0001 x}}$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **A** | Rural | $\sigma_z(x)$ | $\sigma_z = 0.20 x$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **B** | Rural | $\sigma_y(x)$ | $\sigma_y = \frac{0.16 x}{\sqrt{1 + 0.0001 x}}$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **B** | Rural | $\sigma_z(x)$ | $\sigma_z = 0.12 x$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **C** | Rural | $\sigma_y(x)$ | $\sigma_y = \frac{0.11 x}{\sqrt{1 + 0.0001 x}}$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **C** | Rural | $\sigma_z(x)$ | $\sigma_z = \frac{0.08 x}{\sqrt{1 + 0.0002 x}}$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **D** | Rural | $\sigma_y(x)$ | $\sigma_y = \frac{0.08 x}{\sqrt{1 + 0.0001 x}}$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **D** | Rural | $\sigma_z(x)$ | $\sigma_z = \frac{0.06 x}{\sqrt{1 + 0.0015 x}}$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **E** | Rural | $\sigma_y(x)$ | $\sigma_y = \frac{0.06 x}{\sqrt{1 + 0.0001 x}}$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **E** | Rural | $\sigma_z(x)$ | $\sigma_z = \frac{0.03 x}{1 + 0.0003 x}$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **F** | Rural | $\sigma_y(x)$ | $\sigma_y = \frac{0.04 x}{\sqrt{1 + 0.0001 x}}$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **F** | Rural | $\sigma_z(x)$ | $\sigma_z = \frac{0.016 x}{1 + 0.0003 x}$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |

### Urban Dispersion Formulas Audit (Briggs, 1973, Table 1 / McElroy-Pooler, 1968)

| Class | Regime | Parameter | Exact Analytical Formula | Distance Units | Output Units | Valid Range | Source Reference |
| :---: | :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| **A – B** | Urban | $\sigma_y(x)$ | $\sigma_y = \frac{0.32 x}{\sqrt{1 + 0.0004 x}}$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **A – B** | Urban | $\sigma_z(x)$ | $\sigma_z = 0.24 x \sqrt{1 + 0.001 x}$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **C** | Urban | $\sigma_y(x)$ | $\sigma_y = \frac{0.22 x}{\sqrt{1 + 0.0004 x}}$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **C** | Urban | $\sigma_z(x)$ | $\sigma_z = 0.20 x$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **D** | Urban | $\sigma_y(x)$ | $\sigma_y = \frac{0.16 x}{\sqrt{1 + 0.0004 x}}$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **D** | Urban | $\sigma_z(x)$ | $\sigma_z = \frac{0.14 x}{\sqrt{1 + 0.0003 x}}$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **E – F** | Urban | $\sigma_y(x)$ | $\sigma_y = \frac{0.11 x}{\sqrt{1 + 0.0004 x}}$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |
| **E – F** | Urban | $\sigma_z(x)$ | $\sigma_z = \frac{0.08 x}{\sqrt{1 + 0.0015 x}}$ | m | m | $100 - 10000$ m | Briggs (1973) ATDL Report 79, Table 1 |

---

## 4. Gaussian Plume & Mass Conservation Audit

* **Source Framework:** Turner (1970), Seinfeld & Pandis (2016).
* **Implementation:** [`src/atmosim/physics/plume.py`](../src/atmosim/physics/plume.py)
* **Unit Test File:** [`tests/test_plume.py`](../tests/test_plume.py)

### Governing Equation
$$C(x, y, z) = \frac{Q}{2\pi u \sigma_y(x) \sigma_z(x)} \exp\left(-\frac{y^2}{2\sigma_y^2(x)}\right) \left[ \exp\left(-\frac{(z-H)^2}{2\sigma_z^2(x)}\right) + \exp\left(-\frac{(z+H)^2}{2\sigma_z^2(x)}\right) \right]$$

### Independently Derived Analytical Reference Cases Audit

| Case ID | Scenario Description | Input Parameters | Source Equation | Published Output? | Expected Numerical Value | Tolerance |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: |
| **Case 1** | Elevated Stack, Ground Centerline ($y=0, z=0$) | $Q=100\ \text{g/s}, u=5\ \text{m/s}, H=50\ \text{m}, x=1000\ \text{m}$, Class D Rural | Turner (1970) Eq. 3.3 | No (Derived) | $9.232376 \times 10^{-4}\ \text{g/m}^3$ | $\text{rtol} = 10^{-6}$ |
| **Case 2** | Ground Release ($H=0$), Off-Centerline ($y=50, z=0$) | $Q=50\ \text{g/s}, u=2\ \text{m/s}, H=0\ \text{m}, x=500\ \text{m}$, Class A Rural | Turner (1970) Eq. 3.1 | No (Derived) | $6.650950 \times 10^{-4}\ \text{g/m}^3$ | $\text{rtol} = 10^{-6}$ |
| **Case 3** | 3D Elevated Receptor ($y=100, z=30$) | $Q=250\ \text{g/s}, u=4\ \text{m/s}, H=60\ \text{m}, x=2000\ \text{m}$, Class C Rural | Seinfeld & Pandis (2016) Eq. 18.44 | No (Derived) | $5.749977 \times 10^{-4}\ \text{g/m}^3$ | $\text{rtol} = 10^{-6}$ |

---

## 5. End-to-End Equation-to-Code Traceability Map

```text
[ Literature Source ] ────────► [ Documentation ] ────────► [ Implementation ] ────────► [ Pytest Suite ]

1. Pasquill (1961) Table 1    docs/physics_references.md    stability.py:               tests/test_stability.py:
   Turner (1964) Table 1      Section 5                     classify_stability()        TestClassifyStability
   EPA ISC3 (1995)

2. Briggs (1973) Table 1      docs/physics_references.md    dispersion.py:              tests/test_dispersion.py:
   ATDL Report No. 79         Section 6                     compute_sigma_y()           TestDispersionCoefficients
   NOAA / EPA ISC3                                          compute_sigma_z()

3. Turner (1970) AP-26        docs/physics_references.md    plume.py:                   tests/test_plume.py:
   Seinfeld & Pandis (2016)   Section 4                     gaussian_plume_             TestGaussianPlumeBasics
   Chapter 18                                               concentration()             TestMassFluxConservation
                                                            GaussianPlumeModel          TestTextbookAnalyticalReferenceCases

4. Holzworth (1972) AP-101    docs/physics_references.md    (Phase 0 Spec;              (Phase 3 Operational Test)
   EPA AP-101                 Section 7                     Phase 3 Operational)
```
