"""End-to-end integration tests for dataset generation and artifact export."""

import json
from pathlib import Path
import pandas as pd
import pytest

from atmosim.dataset.generator import generate_dataset, write_dataset_artifacts
from atmosim.dataset.schema import get_dataset_schema


def test_generate_dataset_end_to_end():
    result = generate_dataset(random_seed=42)

    assert "splits" in result
    assert "metadata" in result
    assert "leakage_audit" in result

    splits = result["splits"]
    expected_split_names = {"train", "validation", "test", "cross_location_test"}
    assert set(splits.keys()) == expected_split_names

    schema_cols = [c for c, _ in get_dataset_schema()]
    for name, df in splits.items():
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == schema_cols
        assert len(df) > 0

    # Leakage audits must all be PASS
    for audit_name, audit_res in result["leakage_audit"].items():
        assert audit_res["status"] == "PASS", f"Leakage audit {audit_name} failed: {audit_res}"

    # Metadata sample counts must match split DataFrame lengths
    metadata = result["metadata"]
    for name, df in splits.items():
        assert metadata["sample_counts"][name] == len(df)


def test_write_dataset_artifacts(tmp_path: Path):
    result = generate_dataset(random_seed=42)
    output_dir = tmp_path / "benchmark_dataset" / "v1.0"

    write_dataset_artifacts(result, base_dir=output_dir)

    # Check parquet files
    for split_name in result["splits"].keys():
        parquet_file = output_dir / f"{split_name}.parquet"
        assert parquet_file.is_file()
        df_read = pd.read_parquet(parquet_file)
        assert len(df_read) == len(result["splits"][split_name])
        assert list(df_read.columns) == list(result["splits"][split_name].columns)

    # Check metadata.json
    metadata_file = output_dir / "metadata.json"
    assert metadata_file.is_file()
    with open(metadata_file, "r", encoding="utf-8") as f:
        meta_read = json.load(f)
    assert meta_read["dataset_version"] == "v1.0"

    # Check leakage_audit.json
    leakage_file = output_dir / "leakage_audit.json"
    assert leakage_file.is_file()
    with open(leakage_file, "r", encoding="utf-8") as f:
        leakage_read = json.load(f)
    assert leakage_read["feature"]["status"] == "PASS"

    # Check column_dictionary.csv
    col_dict_file = output_dir / "column_dictionary.csv"
    assert col_dict_file.is_file()
    df_col_dict = pd.read_csv(col_dict_file)
    assert {"column_name", "dtype", "description"}.issubset(set(df_col_dict.columns))
    assert len(df_col_dict) == len(get_dataset_schema())

    # Check feature_description.csv
    feat_desc_file = output_dir / "feature_description.csv"
    assert feat_desc_file.is_file()
    df_feat_desc = pd.read_csv(feat_desc_file)
    assert {"feature_name", "category", "description"}.issubset(set(df_feat_desc.columns))


def test_generate_dataset_with_write_artifacts_flag(tmp_path: Path):
    output_dir = tmp_path / "flag_export"
    result = generate_dataset(random_seed=42, write_artifacts=True, output_dir=output_dir)
    assert (output_dir / "train.parquet").is_file()
    assert (output_dir / "metadata.json").is_file()
