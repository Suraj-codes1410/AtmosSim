"""AtmosSim dataset generation package.

Expose the public API for Phase 6 benchmark dataset construction.
"""

from .scenarios import get_predefined_regions, generate_benchmark_scenarios
from .generator import generate_dataset, write_dataset_artifacts
from .features import construct_operational_features
from .targets import extract_targets
from .splits import split_temporal, split_geographic_holdout
from .leakage import audit_feature_leakage, audit_simulator_state_leakage, audit_target_leakage
from .validation import validate_dataset
from .metadata import build_metadata
from .schema import get_dataset_schema

__all__ = [
    "get_predefined_regions",
    "generate_benchmark_scenarios",
    "generate_dataset",
    "write_dataset_artifacts",
    "construct_operational_features",
    "extract_targets",
    "split_temporal",
    "split_geographic_holdout",
    "audit_feature_leakage",
    "audit_simulator_state_leakage",
    "audit_target_leakage",
    "validate_dataset",
    "build_metadata",
    "get_dataset_schema",
]
