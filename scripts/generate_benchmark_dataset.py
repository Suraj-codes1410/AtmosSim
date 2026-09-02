#!/usr/bin/env python3
"""CLI script to generate the canonical Phase 6 benchmark dataset."""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from atmosim.dataset.generator import generate_dataset


def main():
    parser = argparse.ArgumentParser(description="Generate canonical AtmosSim benchmark dataset.")
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic scenario generation (default: 42)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="artifacts/benchmark_dataset/v1.0",
        help="Output directory for artifacts (default: artifacts/benchmark_dataset/v1.0)",
    )
    args = parser.parse_args()

    print(f"=== Starting Benchmark Dataset Generation ===")
    print(f"Random seed: {args.seed}")
    print(f"Target directory: {args.output_dir}")

    result = generate_dataset(
        random_seed=args.seed,
        write_artifacts=True,
        output_dir=args.output_dir,
    )

    out_path = Path(args.output_dir)
    print("\n=== Generation Succeeded ===")
    print(f"Configuration Hash: {result['metadata']['configuration_hash']}")
    print("Splits generated:")
    for split_name, df in result["splits"].items():
        print(f"  - {split_name}: {len(df)} rows, shape={df.shape}")

    print("\nArtifact files created:")
    for f in sorted(out_path.iterdir()):
        print(f"  - {f.name} ({f.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
