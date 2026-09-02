"""
Source Provenance and Uncertainty Modeling for AtmosSim.

Every emission source in AtmosSim carries complete, first-class metadata documenting
the proxy provider, emission parameterization, emission factor provenance, activity profile,
and qualitative uncertainty classification.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class UncertaintyClass(str, Enum):
    """
    Qualitative uncertainty classification for proxy-derived emissions.

    LOW: Directly measured or facility-reported emission rate with high-confidence metadata.
    MEDIUM: Well-supported proxy with localized traffic counts or verified regional emission factors.
    HIGH: Generic OpenStreetMap classification with synthetic/default activity profiles and literature emission factors.
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class SourceProvenance:
    """
    Complete audit record and scientific lineage for an individual emission source.
    """
    source_id: str
    proxy_type: str
    proxy_provider: str
    proxy_id: str
    pollutant: str
    emission_method: str
    emission_factor: float
    emission_factor_units: str
    emission_factor_source: str
    activity_profile: str
    activity_profile_source: str
    uncertainty_class: UncertaintyClass
    retrieval_timestamp: str
    assumptions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize provenance record to JSON-compatible dictionary."""
        return {
            "source_id": self.source_id,
            "proxy_type": self.proxy_type,
            "proxy_provider": self.proxy_provider,
            "proxy_id": self.proxy_id,
            "pollutant": self.pollutant,
            "emission_method": self.emission_method,
            "emission_factor": self.emission_factor,
            "emission_factor_units": self.emission_factor_units,
            "emission_factor_source": self.emission_factor_source,
            "activity_profile": self.activity_profile,
            "activity_profile_source": self.activity_profile_source,
            "uncertainty_class": self.uncertainty_class.value,
            "retrieval_timestamp": self.retrieval_timestamp,
            "assumptions": self.assumptions,
        }
