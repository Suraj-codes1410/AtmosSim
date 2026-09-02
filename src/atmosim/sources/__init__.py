"""
Geographic source proxies, traffic profiles, and emission parameterization module for AtmosSim.
"""

from atmosim.sources.models import (
    ProxyType,
    RoadSegmentProxy,
    IndustrialProxy,
    PointSourceProxy,
)
from atmosim.sources.provenance import (
    UncertaintyClass,
    SourceProvenance,
)
from atmosim.sources.traffic_profiles import (
    TemporalTrafficProfile,
)
from atmosim.sources.emissions import (
    DEFAULT_EMISSION_FACTORS,
    DEFAULT_AADT_BY_CLASS,
    RoadEmissionConfig,
    RoadNetworkSegmenter,
    ProxyEmissionParameterizer,
)

__all__ = [
    "ProxyType",
    "RoadSegmentProxy",
    "IndustrialProxy",
    "PointSourceProxy",
    "UncertaintyClass",
    "SourceProvenance",
    "TemporalTrafficProfile",
    "DEFAULT_EMISSION_FACTORS",
    "DEFAULT_AADT_BY_CLASS",
    "RoadEmissionConfig",
    "RoadNetworkSegmenter",
    "ProxyEmissionParameterizer",
]
