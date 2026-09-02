# AtmosSim — Phase 2 Data Sources & Connectors Reference

## 1. Overview of External Data Providers

AtmosSim Phase 2 interfaces with three primary external data providers:

1. **Open-Meteo Weather Forecast & Historical Reanalysis API**
2. **Open-Meteo / SRTM / Copernicus Elevation API**
3. **OpenStreetMap / Overpass API**

---

## 2. Open-Meteo Meteorology Connector

### 2.1 Provider & Endpoints
* **Forecast Endpoint:** `https://api.open-meteo.com/v1/forecast`
* **Historical Archive Endpoint:** `https://archive-api.open-meteo.com/v1/archive`
* **Temporal Resolution:** 1-hour intervals.
* **Storage Convention:** All timestamps are strictly converted and stored in UTC.

### 2.2 Variables & Units
| Variable Name | Open-Meteo Identifier | Target Units | Description | Missing Value Policy |
| :--- | :--- | :--- | :--- | :--- |
| **Wind Speed** | `wind_speed_10m` | $\text{m/s}$ | 10-meter horizontal wind speed | Fail-fast or linear interpolation |
| **Wind Direction** | `wind_direction_10m` | Degrees [0, 360) | Meteorological direction FROM which wind blows | Circular trigonometric interpolation |
| **Temperature** | `temperature_2m` | °C | 2-meter ambient dry-bulb temperature | Linear interpolation |
| **Relative Humidity** | `relative_humidity_2m` | % | 2-meter relative humidity [0, 100] | Linear interpolation |
| **Boundary Layer Height** | `boundary_layer_height` | $\text{m}$ | Planetary boundary layer height | Fallback default $1000\ \text{m}$ |
| **Surface Pressure** | `surface_pressure` | $\text{hPa}$ | Atmospheric surface pressure | Optional |
| **Direct Normal Irradiance**| `direct_normal_irradiance`| $\text{W/m}^2$ | Solar radiation for stability calculation | Optional |
| **Cloud Cover** | `cloud_cover` | % | Total cloud cover for PGT night/day classes | Optional |

### 2.3 Circular Trigonometric Interpolation for Wind Direction
When interpolating between two hourly records with directions $\theta_0$ and $\theta_1$ at fractional offset $\alpha = (t - t_0) / (t_1 - t_0)$:
$$u_{\text{interp}} = (1 - \alpha)\cos(\theta_0) + \alpha\cos(\theta_1)$$
$$v_{\text{interp}} = (1 - \alpha)\sin(\theta_0) + \alpha\sin(\theta_1)$$
$$\theta(t) = \left(\text{atan2}(v_{\text{interp}}, u_{\text{interp}}) \cdot \frac{180}{\pi} + 360\right) \pmod{360}$$
This eliminates spurious $360^\circ$ swing errors across the North ($359^\circ \leftrightarrow 1^\circ$) boundary.

---

## 3. Terrain & Elevation Ingestion

### 3.1 Source & Geometry
* **Provider:** Open-Meteo Elevation API (SRTM 90m & Copernicus 30m / 90m Global DEMs).
* **Vertical Datum:** EGM96 Mean Sea Level (MSL) in meters above sea level [m a.s.l.].
* **Interpolation:** 2D Bilinear interpolation over regular metric Cartesian grid points $(x_i, y_j)$.
* **Domain Boundary Enforcement:** Out-of-bounds queries raise explicit `ValueError` (no silent extrapolation).

### 3.2 Scientific Limitation Notice
> [!IMPORTANT]
> Ingestion of terrain elevation $z_{\text{terrain}}(x, y)$ provides geometric surface relief. It does **NOT** constitute terrain-aware atmospheric flow (e.g. wind deflection, valley channeling, or gravity waves). Dynamic terrain-flow coupling is scheduled for Phase 3.

---

## 4. OpenStreetMap / Overpass Source Proxy Connector

### 4.1 Query Structure & Bounding Box
* **Endpoint:** `https://overpass-api.de/api/interpreter`
* **Query Format:** Spatially bounded Overpass QL query constrained to the simulation domain bounding box $[lat_{\text{min}}, lon_{\text{min}}, lat_{\text{max}}, lon_{\text{max}}]$.
* **Target Categories:**
  1. `way["highway"~"motorway|trunk|primary|secondary|tertiary|residential|service|unclassified"]`
  2. `way["landuse"="industrial"]`, `relation["landuse"="industrial"]`
  3. `node["man_made"~"chimney|works"]`, `node["power"="generator"]`

### 4.2 Scientific Proxy Qualification
> [!WARNING]
> OpenStreetMap provides geographic proxy geometries, road classifications, and facility tags. It does **NOT** provide physical emission inventories or measured traffic volumes. All emission rates derived from OSM features are proxy-based engineering parameterizations.
