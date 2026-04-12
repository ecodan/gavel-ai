"""Storage utility functions for gavel-ai."""

import hashlib
from pathlib import Path
from typing import Dict


def compute_config_hash(config_files: Dict[str, Path]) -> str:
    """
    Compute SHA256 hash of configuration files.

    For reproducibility verification.

    Args:
        config_files: Dict mapping config name to Path
            (e.g., {"agents": Path(...), "eval_config": Path(...), ...})

    Returns:
        SHA256 hash as hex string

    Raises:
        FileNotFoundError: If any config file doesn't exist
    """
    hasher = hashlib.sha256()

    # Sort by key for consistent ordering
    for key in sorted(config_files.keys()):
        path = config_files[key]
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        # Read file and hash content
        with open(path, "rb") as f:
            hasher.update(f.read())

    return hasher.hexdigest()
