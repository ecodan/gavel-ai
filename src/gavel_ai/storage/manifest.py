"""
Manifest utilities for run metadata and config hashing.

Provides deterministic config hashing for reproducibility verification
per FR-3.2 and FR-8.5.
"""

import hashlib
import json
from typing import Any, Dict


def create_config_hash(configs: Dict[str, Any]) -> str:
    """
    Create deterministic SHA-256 hash of configuration.

    Uses sorted JSON serialization to ensure same configs produce
    same hashes regardless of key order, enabling reproducibility
    verification across runs.

    Args:
        configs: Configuration dictionary to hash

    Returns:
        str: 64-character SHA-256 hash (hexadecimal)

    Example:
        >>> config = {"eval_name": "test", "scenarios": [{"id": "s1"}]}
        >>> hash1 = create_config_hash(config)
        >>> hash2 = create_config_hash(config)
        >>> hash1 == hash2  # Deterministic
        True
    """
    # Sort keys for determinism, use compact separators for consistency
    sorted_json = json.dumps(configs, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(sorted_json.encode()).hexdigest()
