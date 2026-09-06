#!/usr/bin/env python3
"""CLI script to generate the continuous annual 2023 Delhi benchmark dataset."""

import argparse
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from atmosim.dataset.annual_generator import AnnualDatasetGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate continuous full-year Delhi dataset.")
    parser.add_argument("--year", type=int, default=2023, help="Calendar year (default: 2023)")
    parser.add_argument("--city", type=str, default="Delhi", help="City name (default: Delhi)")
    parser.add_argument("--output-dir", type=str, default="artifacts/annual_dataset", help="Output directory")
    args = parser.parse_args()

    print(f"=== Starting Continuous Annual Dataset Generation ===")
    print(f"City: {args.city}")
    print(f"Year: {args.year}")
    print(f"Output Directory: {args.output_dir}")

    t0 = time.time()
    generator = AnnualDatasetGenerator(city_name=args.city, year=args.year)
    df, meta = generator.generate_full_year(output_dir=args.output_dir, save_artifacts=True)
    elapsed = time.time() - t0

    print(f"\n=== Annual Generation Completed in {elapsed:.2f}s ===")
    print(f"Total Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nTarget PM2.5 Statistics (µg/m³):")
    for k, v in meta["target_statistics"].items():
        print(f"  {k}: {v}")

    print(f"\nRegime Distribution:")
    for k, v in meta["regime_distribution"].items():
        print(f"  {k}: {v} hours ({v/len(df)*100:.1f}%)")

    print(f"\nConfidence Level Distribution:")
    for k, v in meta["confidence_level_distribution"].items():
        print(f"  {k}: {v} hours ({v/len(df)*100:.1f}%)")

    print(f"\nKnown Bias Direction Distribution:")
    for k, v in meta["known_bias_distribution"].items():
        print(f"  {k}: {v} hours ({v/len(df)*100:.1f}%)")

    print(f"\nArtifacts Saved:")
    for k, v in meta["artifacts"].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
