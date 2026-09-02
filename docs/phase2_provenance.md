# AtmosSim — Phase 2 Provenance & Uncertainty Framework

## 1. Provenance Schema

Every emission source in AtmosSim carries complete, first-class metadata documenting the data origin, parameterization equations, emission factor citations, and uncertainty class.

```json
{
  "source_id": "osm_road_2001_seg0",
  "proxy_type": "ROAD_SEGMENT",
  "proxy_provider": "OpenStreetMap",
  "proxy_id": "2001",
  "pollutant": "PM2.5",
  "emission_method": "RoadProxy_Length_x_AADT_x_EF_x_DiurnalActivity",
  "emission_factor": 0.14,
  "emission_factor_units": "g PM2.5 / vehicle-km",
  "emission_factor_source": "EMEP/EEA (2019) & CPCB/ARAI (2018) Urban Fleet PM2.5 Composite",
  "activity_profile": "Standard_Urban_Bimodal_Diurnal",
  "activity_profile_source": "AtmosSim Default Urban Bimodal Traffic Activity Parameterization",
  "uncertainty_class": "HIGH",
  "retrieval_timestamp": "2026-09-01T12:00:00Z",
  "assumptions": [
    "AADT proxy count 20000.0 veh/day for highway=primary",
    "Diurnal activity profile Standard_Urban_Bimodal_Diurnal",
    "Ground-level line source discretized to point midpoint at z=0.5m",
    "Unmeasured proxy parameterization (UncertaintyClass: HIGH)"
  ]
}
```

---

## 2. Uncertainty Classification Levels

| Class | Definition | Typical Applications |
| :---: | :--- | :--- |
| **LOW** | Direct continuous emission monitoring system (CEMS) observations or validated facility reports with verified stack geometries. | Regulated industrial point sources, continuous power plant stacks. |
| **MEDIUM** | Localized roadside traffic sensor counts (e.g. inductive loops, ANPR cameras) combined with verified regional fleet composition models. | Instrumented arterial corridors, localized traffic study areas. |
| **HIGH** | OpenStreetMap highway classifications combined with proxy AADT lookups, synthetic diurnal profiles, and literature emission factors. | General-location urban road networks, land-use area proxies. |

---

## 3. Data Lineage & Benchmark Reproducibility

1. **Deterministic Input Hash (`input_hash`):**
   * Computed via SHA-256 over the complete canonical `input_manifest`.
   * Any change in coordinates, date window, meteorology, terrain, or emission factor parameters produces an immediate, detectable change in the input hash.
2. **Auditability:**
   * Downstream ML models or benchmarking suites can trace every simulated concentration value back to the specific road segments, emission factors, and meteorological records responsible.
