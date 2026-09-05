"""Metadata generation utilities for the AtmosSim benchmark dataset.

The ``build_metadata`` function assembles a dictionary that captures the essential
properties of a generated benchmark dataset.  The implementation is deliberately
lightweight – it does not attempt to compute hashes of large binary artefacts;
instead it hashes the string representation of the configuration dict passed in
by the caller so that a reproducible ``configuration_hash`` can be recorded.
"""

from __future__ import annotations

import hashlib
import json
import platform
from datetime import datetime, timezone
from typing import Dict, Any


def _hash_dict(d: Dict[str, Any]) -> str:
    """Return a stable SHA‑256 hash for a dictionary.

    The dictionary is first JSON‑encoded with sorted keys to ensure deterministic
    ordering, then the UTF‑8 bytes are hashed.
    """

    json_str = json.dumps(d, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def build_metadata(
    dataset_version: str,
    feature_version: str,
    canonical_simulator: str,
    canonical_simulator_version: str,
    random_seed: int,
    sample_counts: Dict[str, int],
    feature_count: int,
    configuration: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Construct the ``metadata.json`` dictionary.

    Parameters
    ----------
    dataset_version, feature_version : str
        Version identifiers for the dataset and for the feature definition.
    canonical_simulator, canonical_simulator_version : str
        Identifier and version of the frozen simulator used to generate the data.
    random_seed : int
        Seed used for deterministic scenario generation.
    sample_counts : dict
        Mapping of split name → number of samples.
    feature_count : int
        Total number of feature columns (excluding identifiers and target).
    configuration : dict, optional
        The full configuration dict that drove dataset generation. If omitted an
        empty dict is used and its hash recorded.
    """

    if configuration is None:
        configuration = {}
    metadata: Dict[str, Any] = {
        "dataset_name": "AtmosSim Benchmark Dataset",
        "dataset_version": dataset_version,
        "feature_version": feature_version,
        "creation_date": datetime.now(timezone.utc).isoformat(),
        "generator_version": "AtmosSim dataset generator v1.0",
        "canonical_simulator": canonical_simulator,
        "canonical_simulator_version": canonical_simulator_version,
        "random_seed": random_seed,
        "sample_counts": sample_counts,
        "feature_count": feature_count,
        "configuration_hash": _hash_dict(configuration),
        "software_environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "dataset_scope": "Single synthetic day (2020-01-01), 216-scenario factorial parameter sweep over wind speed, stability class, wind direction, and emission rate — not a multi-day or multi-real-location dataset.",
        "geographic_scope_disclosure": "Regions R001 and R002 share identical synthetic parameter distributions (Delta = 0.000000 across all feature means). The 216 stations represent distinct synthetic parameter combinations, not separate real-world geographical observation sites.",
        "target_physics_disclosure": "Ground-truth target PM2.5 concentrations are unclipped physical outputs up to 1,269.72 ug/m3 under severe nocturnal inversion conditions.",
        "limitations": "Synthetic benchmark parameter sweep; does not guarantee real-world predictive accuracy across complex terrain or multi-source urban airsheds.",
    }
    return metadata

__all__ = ["build_metadata"]
