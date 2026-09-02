"""Unit tests for metadata generation in atmosim.dataset.metadata."""

from atmosim.dataset.metadata import build_metadata, _hash_dict


def test_build_metadata_structure_and_types():
    sample_counts = {"train": 70, "validation": 15, "test": 15}
    meta = build_metadata(
        dataset_version="v1.0",
        feature_version="v1.0",
        canonical_simulator="GaussianPlumeModel",
        canonical_simulator_version="1.0.0",
        random_seed=42,
        sample_counts=sample_counts,
        feature_count=17,
        configuration={"key": "value"},
    )

    assert meta["dataset_name"] == "AtmosSim Benchmark Dataset"
    assert meta["dataset_version"] == "v1.0"
    assert meta["feature_version"] == "v1.0"
    assert meta["canonical_simulator"] == "GaussianPlumeModel"
    assert meta["canonical_simulator_version"] == "1.0.0"
    assert meta["random_seed"] == 42
    assert meta["sample_counts"] == sample_counts
    assert meta["feature_count"] == 17
    assert "creation_date" in meta
    assert "configuration_hash" in meta
    assert "python_version" in meta["software_environment"]
    assert "platform" in meta["software_environment"]
    assert "Synthetic benchmark" in meta["limitations"]


def test_hash_dict_deterministic():
    d1 = {"b": 2, "a": 1, "nested": {"z": 10, "y": 20}}
    d2 = {"nested": {"y": 20, "z": 10}, "a": 1, "b": 2}
    h1 = _hash_dict(d1)
    h2 = _hash_dict(d2)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256
