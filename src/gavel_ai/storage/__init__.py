"""
Storage module for gavel-ai.

Storage abstraction and artifact management.

This module provides Run, Config, and Prompt abstract base classes along with LocalFilesystem
implementations for artifact persistence.

"""

from gavel_ai.core.exceptions import StorageError
from gavel_ai.models.runtime import ArtifactRef, Manifest
from gavel_ai.storage.archive import RunArchiver
from gavel_ai.storage.base import Config, Prompt, Run
from gavel_ai.storage.cleanup import RunCleaner
from gavel_ai.storage.context import RunContext
from gavel_ai.storage.filesystem import LocalFilesystemRun
from gavel_ai.storage.history import RunHistory
from gavel_ai.storage.manifest import create_config_hash

__all__ = [
    "Run",
    "Config",
    "Prompt",
    "ArtifactRef",
    "Manifest",
    "StorageError",
    "LocalFilesystemRun",
    "RunHistory",
    "RunCleaner",
    "RunArchiver",
    "RunContext",
    "create_config_hash",
]
