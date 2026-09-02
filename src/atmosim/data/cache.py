"""
Deterministic caching module for external API responses in AtmosSim.

Provides file-based caching for Open-Meteo, Overpass OSM, and Elevation API responses
to ensure offline reproducibility, rate-limit protection, and deterministic test execution.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union
import hashlib
import json
import os


class DataCache:
    """
    File-based JSON cache for external API query responses.

    Parameters
    ----------
    cache_dir : Optional[Union[str, Path]], optional
        Directory path for cached JSON files. Defaults to '.cache/atmosim' in current working directory
        or '~/.cache/atmosim'.
    enabled : bool, default=True
        Whether caching is active. If False, get() always returns None and set() is a no-op.
    """

    def __init__(
        self,
        cache_dir: Optional[Union[str, Path]] = None,
        enabled: bool = True,
    ) -> None:
        self.enabled = enabled
        if cache_dir is not None:
            self.cache_dir = Path(cache_dir)
        else:
            default_dir = os.environ.get("ATMOSIM_CACHE_DIR", ".cache/atmosim")
            self.cache_dir = Path(default_dir)

        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def generate_key(prefix: str, params: Dict[str, Any]) -> str:
        """
        Generate deterministic SHA-256 hash key from query parameters.

        Parameters
        ----------
        prefix : str
            Category prefix (e.g. 'open_meteo', 'overpass', 'elevation').
        params : Dict[str, Any]
            Query dictionary. Keys are sorted for deterministic serialization.

        Returns
        -------
        str
            Hex-encoded hash key with prefix.
        """
        serialized = json.dumps(params, sort_keys=True, default=str)
        hash_digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return f"{prefix}_{hash_digest}"

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached JSON payload if present."""
        if not self.enabled:
            return None
        file_path = self.cache_dir / f"{key}.json"
        if file_path.is_file():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return None
        return None

    def set(self, key: str, data: Dict[str, Any]) -> None:
        """Save JSON payload to cache directory."""
        if not self.enabled:
            return
        file_path = self.cache_dir / f"{key}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, sort_keys=True)
        except OSError:
            pass

    def clear(self) -> None:
        """Clear all cached files in cache directory."""
        if self.cache_dir.exists():
            for f in self.cache_dir.glob("*.json"):
                try:
                    f.unlink()
                except OSError:
                    pass
