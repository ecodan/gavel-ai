"""
Base classes and interfaces for storage.

Defines Run, Config, and Prompt ABCs that all storage implementations must inherit from.
Per Architecture Decision 8: Domain-driven storage abstraction with clean interfaces.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict

from gavel_ai.telemetry import get_tracer

if TYPE_CHECKING:
    from gavel_ai.models.runtime import ArtifactRef


class Run(ABC):
    """
    Abstract base class for run storage.

    Per Architecture Decision 8: Domain-driven storage abstraction.
    Each Run implementation knows how to persist and load its own artifacts.

    v1 Implementations: LocalFilesystemRun (Story 6.2)
    v2+ Implementations: DatabaseRun, S3Run, ExperimentTrackingRun
    """

    def __init__(self, run_id: str, metadata: Dict[str, Any]):
        """
        Initialize run with ID and metadata.

        Args:
            run_id: Unique identifier for this run (e.g., "run-20251230-120000")
            metadata: Run metadata (eval_name, timestamp, config_hash, etc.)
        """
        self.run_id = run_id
        self.metadata = metadata
        self.tracer = get_tracer(__name__)

    @abstractmethod
    async def save(self) -> str:
        """
        Persist run artifacts to storage.

        Returns:
            str: Storage location/path of saved run

        Raises:
            StorageError: On save failures
        """
        pass

    @staticmethod
    @abstractmethod
    async def load(run_id: str, storage_path: str = ".gavel") -> "Run":
        """
        Load run from storage by ID.

        Args:
            run_id: Unique run identifier
            storage_path: Storage location path (default: ".gavel")

        Returns:
            Run: Loaded run instance with all artifacts

        Raises:
            StorageError: If run not found or load fails
        """
        pass

    @property
    @abstractmethod
    def artifacts(self) -> Dict[str, "ArtifactRef"]:
        """
        Get dictionary of run artifacts.

        Returns:
            Dict mapping artifact names to ArtifactRef instances.

        Example:
            {
                "manifest": ArtifactRef(path="manifest.json", type="json", size=1024),
                "results": ArtifactRef(path="results.jsonl", type="jsonl", size=50000),
                "report": ArtifactRef(path="report.html", type="html", size=25000)
            }
        """
        pass


class Config(ABC):
    """
    Abstract base class for configuration loading/saving.

    Per Architecture Decision 8: Pluggable config storage.

    v1 Implementations: LocalFileConfig (loads JSON/YAML files)
    v2+ Implementations: DatabaseConfig, PromptServerConfig
    """

    def __init__(self, config_path: str):
        """
        Initialize config with path.

        Args:
            config_path: Path to configuration (file, URL, database key, etc.)
        """
        self.config_path = config_path
        self.tracer = get_tracer(__name__)

    @abstractmethod
    async def load(self) -> Dict[str, Any]:
        """
        Load configuration from storage.

        Returns:
            Dict containing configuration data

        Raises:
            StorageError: On load failures
        """
        pass

    @abstractmethod
    async def save(self, config_data: Dict[str, Any]) -> None:
        """
        Save configuration to storage.

        Args:
            config_data: Configuration dictionary to persist

        Raises:
            StorageError: On save failures
        """
        pass


class Prompt(ABC):
    """
    Abstract base class for prompt template loading/saving.

    Per Architecture Decision 8: Pluggable prompt storage.
    Supports versioned prompts (v1, v2, latest).

    v1 Implementations: LocalFilePrompt (loads TOML templates)
    v2+ Implementations: PromptServerPrompt, DatabasePrompt
    """

    def __init__(self, prompt_name: str, prompt_path: str):
        """
        Initialize prompt with name and path.

        Args:
            prompt_name: Prompt identifier (e.g., "assistant", "researcher")
            prompt_path: Path to prompt storage location
        """
        self.prompt_name = prompt_name
        self.prompt_path = prompt_path
        self.tracer = get_tracer(__name__)

    @abstractmethod
    async def load(self, version: str = "latest") -> str:
        """
        Load prompt template by version.

        Args:
            version: Version identifier (e.g., "v1", "v2", "latest")

        Returns:
            str: Prompt template content

        Raises:
            StorageError: If version not found or load fails
        """
        pass

    @abstractmethod
    async def save(self, version: str, content: str) -> None:
        """
        Save prompt template with version.

        Args:
            version: Version identifier to save under
            content: Prompt template content

        Raises:
            StorageError: On save failures
        """
        pass
