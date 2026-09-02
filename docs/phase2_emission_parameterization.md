# AtmosSim — Phase 2 Proxy-to-Emission Parameterization & Scientific Audit

## 1. Governing Formulation

For a discrete road segment of length $L$ [meters], the instantaneous primary PM2.5 emission rate $Q_{\text{road}}(t)$ in $[\text{g/s}]$ is parameterized as:

$$Q_{\text{road}}(t) = L_{\text{km}} \times V(t) \times \text{EF} \times \frac{1}{3600}$$

where:
* $L_{\text{km}} = \frac{L_{\text{meters}}}{1000}$ is the segment length in kilometers [$\text{km}$].
* $V(t) = \text{AADT}_{\text{class}} \times \frac{f(t)}{24}$ is the proxy hourly traffic volume in [$\text{vehicles / hour}$].
* $\text{EF}$ is the composite fleet PM2.5 emission factor in [$\text{g PM2.5 / vehicle-km}$].
* $\frac{1}{3600}$ converts hours to seconds [$\text{hours / second}$].

### Dimensional Verification
$$[\text{km}] \times \left[\frac{\text{vehicles}}{\text{hour}}\right] \times \left[\frac{\text{g PM2.5}}{\text{vehicle} \cdot \text{km}}\right] \times \left[\frac{1\ \text{hour}}{3600\ \text{s}}\right] = \left[\frac{\text{g PM2.5}}{\text{s}}\right]$$

---

## 2. Emission Factor Provenance & Scope Audit ($0.03 - 0.22\ \text{g/veh-km}$)

### 2.1 Scope & Pollutant Definition
* **Pollutant:** Primary particulate matter with aerodynamic diameter $\le 2.5\ \mu\text{m}$ (PM2.5).
* **Included Components:** Tailpipe exhaust PM2.5 + non-exhaust brake wear PM2.5 + non-exhaust tyre wear PM2.5.
* **Explicit Exclusion:** Resuspended road surface mineral dust (silt loading AP-42 mechanism) is **NOT** included in these vehicle emission factors.

### 2.2 Literature Provenance & Source Tables
1. **EMEP/EEA Air Pollutant Emission Inventory Guidebook (2019):**
   * *Chapter 1.A.3.b Road Transport, Table 3-17:* Tier 2 exhaust emission factors for passenger cars, light commercial vehicles (LCVs), and heavy-duty vehicles (HDVs).
   * *Chapter 1.A.3.b Road Transport, Table 3-23:* Tier 2 non-exhaust emission factors for brake wear and tyre wear ($0.007\ \text{g/km}$ brake PM2.5 + $0.005\ \text{g/km}$ tyre PM2.5 for passenger cars; higher for HDVs).
2. **CPCB & ARAI (2018):**
   * *"Emission Factor Development for Indian Vehicles"*, Central Pollution Control Board (CPCB) and Automotive Research Association of India (ARAI).
   * Composite fleet exhaust emission factors for mixed Indian urban traffic fleets (2-wheelers, 3-wheelers, passenger cars, diesel LCVs, HCVs).

### 2.3 Road-Class to Emission Factor Mapping Rationale
| Highway Class | EF [g PM2.5 / veh-km] | Fleet Composition & Driving Regime Rationale |
| :--- | :---: | :--- |
| `motorway` | 0.22 | High fraction of heavy diesel commercial trucks ($\approx 15-25\%$), high cruising speed ($80-100\ \text{km/h}$), elevated tire wear. |
| `trunk` | 0.18 | Inter-city arterial corridors with mixed freight and long-distance bus traffic. |
| `primary` | 0.14 | Urban arterial corridors with mixed stop-and-go congestion, elevated brake wear, $\approx 5-10\%$ buses/trucks, $35\%$ cars, $45\%$ 2W/3W. |
| `secondary` | 0.10 | City collector / sub-arterial roads with low heavy-duty fraction ($\approx 2-5\%$). |
| `tertiary` | 0.08 | Urban distributor streets dominated by light-duty vehicles and 2-wheelers. |
| `residential` | 0.05 | Low-speed neighborhood streets with light-duty vehicles and smooth driving. |
| `service` | 0.03 | Minor parking alleys and low-speed access ways. |

---

## 3. AADT (Annual Average Daily Traffic) Derivation & Proxy Classification

> [!WARNING]
> OpenStreetMap road tags provide highway classifications (`motorway`, `primary`, etc.), but **DO NOT provide measured traffic counts**.

* **Proxy Engineering Defaults:** The default AADT values are engineering proxy estimates based on urban road design capacities (Indian Road Congress IRC:106-1990) and urban mobility baseline studies (e.g. RITES 2010; Guttikunda et al., 2014):
  * `motorway`: $45,000\ \text{veh/day}$
  * `trunk`: $30,000\ \text{veh/day}$
  * `primary`: $20,000\ \text{veh/day}$
  * `secondary`: $10,000\ \text{veh/day}$
  * `tertiary`: $4,000\ \text{veh/day}$
  * `residential`: $1,200\ \text{veh/day}$
  * `service`: $400\ \text{veh/day}$
* **User Configurable:** Users can override proxy AADT with empirical traffic counts via `RoadEmissionConfig(aadt_by_class=...)`.

---

## 4. Temporal Traffic Activity Profiles

The diurnal hourly multiplier $f(h)$ is normalized such that:

$$\frac{1}{24} \sum_{h=0}^{23} f_h = 1.000000$$

### Normalized 24-Hour Bimodal Diurnal Curve
```text
Hour (UTC)   Factor f_h    Description
00:00        0.25          Overnight minimum
04:00        0.22          Early morning trough
08:00        1.60          Morning commute peak
12:00        1.10          Midday plateau
17:00        1.70          Evening rush hour peak
18:00        1.95          Evening peak maximum
22:00        0.50          Night decline
```
* **Weekend Scaling:** Multiplier of $0.85$ (15% traffic reduction) applied on Saturdays and Sundays.

---

## 5. Road Initial Dimensions $\sigma_0 = (5.0, 5.0, 1.5)\ \text{m}$ Provenance

* **Regulatory Modeling Origin:** Grounded in U.S. EPA CALINE4 / AERMOD / ISC3 volume/line-source initial mixing zone guidance (EPA-454/B-95-003b).
* **Physical Basis:**
  * For a discrete road segment of traffic lane width $W \approx 10-20\ \text{m}$:
    $$\sigma_{y0} \approx \frac{W}{2.15} \approx \frac{10.75\ \text{m}}{2.15} = 5.0\ \text{m}$$
  * For vehicle wake turbulence height $H_{\text{wake}} \approx 3.2\ \text{m}$:
    $$\sigma_{z0} \approx \frac{H_{\text{wake}}}{2.15} \approx \frac{3.2\ \text{m}}{2.15} = 1.5\ \text{m}$$
  * Horizontal isotropy: $\sigma_{x0} = \sigma_{y0} = 5.0\ \text{m}$.
* **Classification:** Classified as an **EPA volume source initial mixing zone heuristic**, user-configurable in `RoadEmissionConfig(initial_sigma=...)`.

---

## 6. Industrial Proxy Safety Audit

* Industrial polygons (`landuse=industrial`) and point nodes (`man_made=chimney`) are preserved as geographic land-use proxies with `emission_status='unavailable'`.
* They are strictly **NOT** added to the active `sources` list passed to the `GaussianPuffEngine` unless explicit user-provided emission rates and stack parameters are supplied, preventing unmeasured phantom emissions.
