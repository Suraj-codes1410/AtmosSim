#!/usr/bin/env python3
"""CLI script to validate the canonical Phase 6 benchmark dataset release."""

import argparse
import json
import sys
from pathlib import Path
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from atmosim.dataset.validation import validate_dataset
from atmosim.dataset.schema import get_dataset_schema


def main():
    parser = argparse.ArgumentParser(description="Validate canonical AtmosSim benchmark dataset release.")
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default="artifacts/benchmark_dataset/v1.0",
        help="Directory containing benchmark dataset release (default: artifacts/benchmark_dataset/v1.0)",
    )
    args = parser.parse_args()
    base_dir = Path(args.dataset_dir)

    print(f"=== Validating Benchmark Dataset Release ===")
    print(f"Directory: {base_dir.resolve()}")

    if not base_dir.exists():
        print(f"ERROR: Dataset directory {base_dir} does not exist.", file=sys.stderr)
        sys.exit(1)

    # 1. Verify required files
    required_files = [
        "train.parquet",
        "validation.parquet",
        "test.parquet",
        "cross_location_test.parquet",
        "metadata.json",
        "leakage_audit.json",
        "column_dictionary.csv",
        "feature_description.csv",
    ]
    missing = [f for f in required_files if not (base_dir / f).is_file()]
    if missing:
        print(f"ERROR: Missing required artifact files: {missing}", file=sys.stderr)
        sys.exit(1)
    print("All required artifact files are present.")

    # 2. Check metadata
    with open(base_dir / "metadata.json", "r", encoding="utf-8") as f:
        metadata = json.load(f)
    print(f"Metadata verified: Version={metadata.get('dataset_version')}, Simulator={metadata.get('canonical_simulator')}")
    print(f"Configuration Hash: {metadata.get('configuration_hash')}")

    # 3. Check leakage audit
    with open(base_dir / "leakage_audit.json", "r", encoding="utf-8") as f:
        leakage = json.load(f)
    for k, v in leakage.items():
        if v.get("status") != "PASS":
            print(f"ERROR: Leakage audit '{k}' failed: {v}", file=sys.stderr)
            sys.exit(1)
        print(f"Leakage audit '{k}': PASS")

    # 4. Validate each split DataFrame
    schema = get_dataset_schema()
    for split_name in ["train", "validation", "test", "cross_location_test"]:
        split_file = base_dir / f"{split_name}.parquet"
        df = pd.read_parquet(split_file)
        print(f"Validating {split_name} ({len(df)} rows, {len(df.columns)} columns)...")
        validate_dataset(df, schema=schema, leakage_audit=leakage)
        print(f"  -> {split_name}: VALID")

    # 5. Check dictionaries
    col_dict = pd.read_csv(base_dir / "column_dictionary.csv")
    feat_desc = pd.read_csv(base_dir / "feature_description.csv")
    print(f"Column dictionary: {len(col_dict)} entries verified.")
    print(f"Feature description: {len(feat_desc)} features documented.")

    print("\n=== All Dataset Validation Checks PASSED Cleanly ===")


if __name__ == "__main__":
    main()
