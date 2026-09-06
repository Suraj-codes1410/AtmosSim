#!/usr/bin/env python3
"""
Multi-Year Multi-City Continuous Dataset Generator for AtmosSim.

Generates continuous hourly air quality datasets across 7 historical years (2018-2024)
for the 4 validated Indian megacities (Delhi, Mumbai, Pune, Bengaluru), scaling the
dataset to ~100-200 MB with full quality-flagging and physical lineage.
"""

from __future__ import annotations
import argparse
import json
import time
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from atmosim.dataset.annual_generator import AnnualDatasetGenerator, CITY_PROFILES


def main():
    parser = argparse.ArgumentParser(description="Generate Multi-Year Multi-City Continuous Air Quality Datasets.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="artifacts/multiyear_dataset",
        help="Directory to save multi-year datasets",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=2018,
        help="Start calendar year (inclusive)",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=2024,
        help="End calendar year (inclusive)",
    )
    parser.add_argument(
        "--cities",
        nargs="+",
        default=["Delhi", "Mumbai", "Pune", "Bengaluru"],
        help="List of cities to simulate",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    years = list(range(args.start_year, args.end_year + 1))

    print("================================================================================")
    print("      AtmosSim: Multi-Year Multi-City Continuous Air Quality Dataset Scale      ")
    print("================================================================================")
    print(f"Target Cities ({len(args.cities)}): {', '.join(args.cities)}")
    print(f"Target Years  ({len(years)}): {args.start_year} - {args.end_year} ({len(years)} continuous years)")
    print(f"Total City-Years to Generate: {len(args.cities) * len(years)}")
    print(f"Output Directory: {out_dir.resolve()}\n")

    t_start = time.perf_counter()
    all_city_dfs: Dict[str, List[pd.DataFrame]] = {c: [] for c in args.cities}
    master_dfs: List[pd.DataFrame] = []

    total_records = 0

    for city in args.cities:
        print(f"\n--------------------------------------------------------------------------------")
        print(f"=== PROCESSING CITY: {city.upper()} ===")
        print(f"--------------------------------------------------------------------------------")
        generator = AnnualDatasetGenerator(city_name=city)

        for yr in years:
            t0 = time.perf_counter()
            generator.year = yr
            df_yr, meta_yr = generator.generate_full_year(
                output_dir=out_dir / "annual_slices",
                save_artifacts=True,
            )
            elapsed = time.perf_counter() - t0
            all_city_dfs[city].append(df_yr)
            master_dfs.append(df_yr)
            total_records += len(df_yr)

            mean_val = df_yr["target_pm25"].mean()
            max_val = df_yr["target_pm25"].max()
            p95_val = df_yr["target_pm25"].quantile(0.95)
            print(f"  [{city:9s} - {yr}] {len(df_yr):5d} hrs in {elapsed:4.1f}s | "
                  f"Mean: {mean_val:6.2f} ug/m3 | p95: {p95_val:6.2f} | Max: {max_val:7.2f} ug/m3")

        # Save continuous multi-year dataset per city
        city_full_df = pd.concat(all_city_dfs[city], ignore_index=True)
        city_parquet = out_dir / f"{city.lower()}_{args.start_year}_{args.end_year}_continuous.parquet"
        city_csv = out_dir / f"{city.lower()}_{args.start_year}_{args.end_year}_continuous.csv"
        city_meta_path = out_dir / f"{city.lower()}_{args.start_year}_{args.end_year}_metadata.json"

        city_full_df.to_parquet(city_parquet, index=False)
        city_full_df.to_csv(city_csv, index=False)

        city_meta = {
            "dataset_name": f"AtmosSim_{city}_{args.start_year}_{args.end_year}_Continuous",
            "city": city,
            "start_year": args.start_year,
            "end_year": args.end_year,
            "total_hourly_records": len(city_full_df),
            "aadt_calibration_factor": CITY_PROFILES[city]["aadt_calibration_factor"],
            "inventory_source": CITY_PROFILES[city]["inventory_source"],
            "climate_zone": CITY_PROFILES[city]["climate_zone"],
            "summary_statistics": {
                "mean_pm25": round(float(city_full_df["target_pm25"].mean()), 2),
                "median_pm25": round(float(city_full_df["target_pm25"].median()), 2),
                "p95_pm25": round(float(city_full_df["target_pm25"].quantile(0.95)), 2),
                "max_pm25": round(float(city_full_df["target_pm25"].max()), 2),
            },
            "regime_distribution": city_full_df["regime"].value_counts().to_dict(),
            "confidence_distribution": city_full_df["confidence_level"].value_counts().to_dict(),
            "known_bias_distribution": city_full_df["known_bias_direction"].value_counts().to_dict(),
        }
        with open(city_meta_path, "w", encoding="utf-8") as f:
            json.dump(city_meta, f, indent=2)

        print(f"  --> Saved {city} {args.start_year}-{args.end_year} ({len(city_full_df):,} hrs) to Parquet & CSV")

    # Save Unified Master Consolidated Multi-City Multi-Year Dataset
    print("\n--------------------------------------------------------------------------------")
    print("=== BUILDING CONSOLIDATED MULTI-CITY MULTI-YEAR MASTER RELEASE ===")
    print("--------------------------------------------------------------------------------")
    master_df = pd.concat(master_dfs, ignore_index=True)
    master_parquet = out_dir / f"multicity_{args.start_year}_{args.end_year}_continuous_master.parquet"
    master_csv = out_dir / f"multicity_{args.start_year}_{args.end_year}_continuous_master.csv"
    master_meta_path = out_dir / f"multicity_{args.start_year}_{args.end_year}_master_metadata.json"

    print(f"Writing master Parquet ({len(master_df):,} total rows)...")
    master_df.to_parquet(master_parquet, index=False)
    print(f"Writing master CSV ({len(master_df):,} total rows)...")
    master_df.to_csv(master_csv, index=False)

    master_meta = {
        "dataset_name": f"AtmosSim_MultiCity_{args.start_year}_{args.end_year}_Master_Continuous",
        "version": "2.0",
        "cities": args.cities,
        "start_year": args.start_year,
        "end_year": args.end_year,
        "total_hourly_records": len(master_df),
        "total_city_years": len(args.cities) * len(years),
        "city_profiles": {c: CITY_PROFILES[c] for c in args.cities},
        "per_city_records": {c: int((master_df["city"] == c).sum()) for c in args.cities},
        "overall_summary_statistics": {
            "mean_pm25": round(float(master_df["target_pm25"].mean()), 2),
            "median_pm25": round(float(master_df["target_pm25"].median()), 2),
            "p95_pm25": round(float(master_df["target_pm25"].quantile(0.95)), 2),
            "max_pm25": round(float(master_df["target_pm25"].max()), 2),
        },
        "regime_distribution": master_df["regime"].value_counts().to_dict(),
        "confidence_distribution": master_df["confidence_level"].value_counts().to_dict(),
        "known_bias_distribution": master_df["known_bias_direction"].value_counts().to_dict(),
    }
    with open(master_meta_path, "w", encoding="utf-8") as f:
        json.dump(master_meta, f, indent=2)

    total_time = time.perf_counter() - t_start
    print(f"\n================================================================================")
    print(f"Multi-Year Generation Complete in {total_time:.1f}s ({total_time/60:.2f} mins)")
    print(f"Total Records Generated: {len(master_df):,} hourly timesteps ({len(master_df)*31:,} data points)")
    print(f"Master Parquet: {master_parquet} ({master_parquet.stat().st_size / (1024*1024):.2f} MB)")
    print(f"Master CSV:     {master_csv} ({master_csv.stat().st_size / (1024*1024):.2f} MB)")
    print(f"================================================================================\n")


if __name__ == "__main__":
    main()
