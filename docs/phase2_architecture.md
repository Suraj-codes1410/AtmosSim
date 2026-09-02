# AtmosSim — Phase 2 System Architecture & Ingestion Pipeline

## 1. System Overview

Phase 2 establishes the **general-location environmental and source ingestion infrastructure** for AtmosSim. It transforms an arbitrary geographic coordinate `(lat, lon)` and continuous date range `(start_time, end_time)` into a fully validated, provenance-complete `SimulationInput` object consumable by the frozen Phase 1 Gaussian Puff engine.

```text
                                  USER REQUEST
                       (latitude, longitude, date_range)
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │    Domain & Coordinate Setup  │
                       │    LocalCoordinateSystem      │
                       └───────────────┬───────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        ▼                              ▼                              ▼
 ┌──────────────┐              ┌──────────────┐              ┌──────────────────┐
 │  Open-Meteo  │              │   Terrain    │              │ OpenStreetMap /  │
 │  Meteorology │              │  Elevation   │              │     Overpass     │
 └──────┬───────┘              └──────┬───────┘              └────────┬─────────┘
        │                             │                               │
        ▼                             ▼                               ▼
 ┌──────────────┐              ┌──────────────┐              ┌──────────────────┐
 │ Normalized   │              │ 2D Gridded   │              │ Spatially Bounded│
 │ Time Series  │              │ TerrainField │              │ Road/Ind Proxies │
 └──────┬───────┘              └──────┬───────┘              └────────┬─────────┘
        │                             │                               │
        │                             │                               ▼
        │                             │                      ┌──────────────────┐
        │                             │                      │ Road Segmenter & │
        │                             │                      │ Proxy-to-Emission│
        │                             │                      │ Q(t) in [g/s]    │
        │                             │                      └────────┬─────────┘
        │                             │                               │
        └──────────────────────┬──────┴───────────────────────────────┘
                               ▼
               ┌───────────────────────────────┐
               │    SimulationInput Assembler  │
               │  - Metric Cartesian alignment │
               │  - Complete Audit Manifest    │
               │  - SHA-256 Fingerprint Hash   │
               └───────────────┬───────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │  Frozen Phase 1 Puff Engine   │
               │  - Time-dependent advection   │
               │  - 3D Gaussian dispersion     │
               │  - Superimposed concentrations│
               └───────────────────────────────┘
```

---

## 2. Core Architectural Separation

To maintain strict scientific integrity, AtmosSim Phase 2 enforces a strict separation of concerns:

| Component Layer | Responsibility | Input | Output | Scientific Classification |
| :--- | :--- | :--- | :--- | :--- |
| **External Connectors** (`atmosim.data`) | Connects to external APIs, parses schemas, manages offline caching. | Raw HTTP query / parameters | Normalized raw feature records | **External Observed / Reanalysis Data** |
| **Terrain Field** (`atmosim.data.terrain`) | Manages 2D surface elevation $z(x, y)$, interpolation, and domain bounds. | Geodetic / Cartesian grid coords | Surface elevation in meters [m] | **Topographic Surface Geometry** |
| **Source Proxy Models** (`atmosim.sources.models`) | Segments road geometries, classifies infrastructure features. | OSM vector features | `RoadSegmentProxy`, `IndustrialProxy` | **Mapped Physical Infrastructure Proxies** |
| **Emission Engine** (`atmosim.sources.emissions`) | Computes time-dependent pollutant emission rate $Q(t)$ [g/s]. | Road length, AADT, diurnal profile, EF | `EmissionSource` with $Q(t)$ | **Proxy-Derived Emission Estimates** |
| **Simulation Assembler** (`atmosim.simulation`) | Assembles, validates, and hashes the complete input environment. | Location, date range, parameters | `SimulationInput` & JSON Manifest | **Assembled Simulation Inputs** |
| **Phase 1 Physics Engine** (`atmosim.physics.puff`) | Evaluates atmospheric advection, dispersion, and receptor concentrations. | `SimulationInput`, receptor coords | Concentration field $C(x, y, z)$ [g/m³] | **Analytical/Numerical Dispersion Physics** |

---

## 3. Data Flow & Unit Contracts

All physical units are standardized across module boundaries:

1. **Spatial Coordinates:** Projected metric Cartesian $(x, y)$ in meters (+x = East, +y = North) anchored at domain center `(origin_lat, origin_lon)` via `LocalCoordinateSystem`.
2. **Road Length:** Calculated strictly in Cartesian metric meters ($L_{\text{meters}}$) and converted to kilometers ($L_{\text{km}} = L_{\text{meters}} / 1000$).
3. **Meteorological Wind:** Speed in meters per second [m/s], direction in degrees clockwise from true North [°]. Converted internally to Cartesian advection velocity $(u, v)$ via `meteorological_wind_to_cartesian()`.
4. **Pollutant Emissions:** Instantaneous mass rate $Q(t)$ strictly in grams per second [g/s] of primary PM2.5.
5. **Receptor Concentrations:** Micrograms per cubic meter [$\mu\text{g}/\text{m}^3$] or grams per cubic meter [$\text{g}/\text{m}^3$].

---

## 4. Offline Determinism & Caching

Every external connector (`OpenMeteoConnector`, `TerrainConnector`, `OverpassConnector`) interacts through `DataCache`.
* Cache keys are computed deterministically via SHA-256 hashes of sorted query parameters.
* All unit and integration tests run offline without live network dependencies using cached fixtures in `tests/fixtures/`.
