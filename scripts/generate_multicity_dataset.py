#!/usr/bin/env python3
"""
Multi-City Annual Continuous Dataset Generator for AtmosSim.

Generates 8,760-hour continuous datasets across diverse geographic and meteorological
regimes (Delhi, Mumbai, Pune, Bengaluru) with immediate physical sanity checks.
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from atmosim.dataset.annual_generator import AnnualDatasetGenerator, CITY_PROFILES

# Expected realistic published air quality bounds per city (CPCB / SAFAR / NCAP)
CITY_BENCHMARK_EXPECTATIONS = {
    "Delhi": {
        "expected_mean_pm25_range": (120.0, 220.0),
        "expected_max_hourly_range": (1200.0, 2500.0),
        "notes": "Indo-Gangetic Plain severe winter inversion + transboundary crop smoke basin",
    },
    "Mumbai": {
        "expected_mean_pm25_range": (45.0, 85.0),
        "expected_max_hourly_range": (350.0, 900.0),
        "notes": "Coastal maritime boundary layer, land-sea breeze ventilation, humid maritime dispersion",
    },
    "Pune": {
        "expected_mean_pm25_range": (40.0, 75.0),
        "expected_max_hourly_range": (300.0, 800.0),
        "notes": "Deccan elevated plateau, nocturnal valley radiation cooling, moderate daytime convection",
    },
    "Bengaluru": {
        "expected_mean_pm25_range": (30.0, 60.0),
        "expected_max_hourly_range": (200.0, 600.0),
        "notes": "Southern elevated plateau, good dispersion ventilation, urban corridor hotspots",
    },
}


def generate_and_audit_city(city_name: str, year: int = 2023, output_dir: str = "artifacts/annual_dataset") -> dict:
    print(f"\n=======================================================")
    print(f"   GENERATING CONTINUOUS ANNUAL DATASET FOR {city_name.upper()} ({year})")
    print(f"=======================================================")

    t0 = time.time()
    generator = AnnualDatasetGenerator(city_name=city_name, year=year)
    df, meta = generator.generate_full_year(output_dir=output_dir, save_artifacts=True)
    elapsed = time.time() - t0

    stats = meta["target_statistics"]
    mean_val = stats["mean_pm25"]
    max_val = stats["max_pm25"]
    p95_val = stats["p95_pm25"]
    median_val = stats["median_pm25"]

    # Sanity audit against real city expectations
    bench = CITY_BENCHMARK_EXPECTATIONS.get(city_name, {})
    mean_min, mean_max = bench.get("expected_mean_pm25_range", (20.0, 300.0))
    max_min, max_max = bench.get("expected_max_hourly_range", (100.0, 3000.0))

    mean_pass = mean_min <= mean_val <= mean_max
    max_pass = max_min <= max_val <= max_max

    print(f"\n[Generation Succeeded in {elapsed:.1f}s]")
    print(f"Total Hours: {len(df)} | Road Segments: {meta['road_segments_count']}")
    print(f"PM2.5 Mean:   {mean_val:.2f} µg/m³ (Expected: {mean_min}-{mean_max} µg/m³) -> {'[PASS]' if mean_pass else '[WARNING]'}")
    print(f"PM2.5 Median: {median_val:.2f} µg/m³")
    print(f"PM2.5 p95:    {p95_val:.2f} µg/m³")
    print(f"PM2.5 Max:    {max_val:.2f} µg/m³ (Expected: {max_min}-{max_max} µg/m³) -> {'[PASS]' if max_pass else '[WARNING]'}")

    print(f"\nRegimes:")
    for reg, cnt in meta["regime_distribution"].items():
        print(f"  - {reg}: {cnt} hrs ({cnt/len(df)*100:.1f}%)")

    audit = {
        "city": city_name,
        "year": year,
        "elapsed_seconds": round(elapsed, 1),
        "total_hours": len(df),
        "road_segments": meta["road_segments_count"],
        "mean_pm25": mean_val,
        "max_pm25": max_val,
        "median_pm25": median_val,
        "p95_pm25": p95_val,
        "mean_in_expected_range": mean_pass,
        "max_in_expected_range": max_pass,
        "regimes": meta["regime_distribution"],
    }
    return audit


def main():
    parser = argparse.ArgumentParser(description="Multi-City Annual Dataset Generator.")
    parser.add_argument("--year", type=int, default=2023)
    parser.add_argument("--cities", nargs="+", default=["Mumbai", "Pune", "Bengaluru"])
    parser.add_argument("--output-dir", type=str, default="artifacts/annual_dataset")
    args = parser.parse_args()

    audits = []
    for city in args.cities:
        audit = generate_and_audit_city(city_name=city, year=args.year, output_dir=args.output_dir)
        audits.append(audit)

    print("\n=======================================================")
    print("           MULTI-CITY ANNUAL AUDIT SUMMARY             ")
    print("=======================================================")
    for a in audits:
        status = "ALL PASS" if a["mean_in_expected_range"] and a["max_in_expected_range"] else "CHECK WARNINGS"
        print(f"{a['city']:10s} | Mean: {a['mean_pm25']:6.2f} µg/m³ | Median: {a['median_pm25']:6.2f} µg/m³ | Max: {a['max_pm25']:7.2f} µg/m³ | Status: {status}")


if __name__ == "__main__":
    main()
