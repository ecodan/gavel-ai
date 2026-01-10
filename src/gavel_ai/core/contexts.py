"""
Evaluation and run contexts for gavel-ai workflows.

Provides:
- EvalContext (ABC): Abstract interface for evaluation configuration access
- RunContext (ABC): Abstract interface for run artifact access
- LocalFileSystemEvalContext: Local filesystem implementation of EvalContext
- LocalRunContext: Local filesystem implementation of RunContext

Per Storage Abstraction Specification: Contexts expose DataSource objects,
not data directly. Steps call .read() or .write() on data sources.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Optional

from gavel_ai.core.adapters.backends import LocalStorageBackend
from gavel_ai.core.adapters.data_sources import (
    MultiFormatDataSource,
    RecordDataSource,
    StructDataSource,
)
from gavel_ai.core.config import EvalConfig, Scenario
from gavel_ai.core.exceptions import ResourceNotFoundError


class EvalContext(ABC):
    """
    Evaluation configuration context (Abstract Base Class).

    Provides read-only access to evaluation configuration artifacts
    (agents, prompts, judges, scenarios) through DataSource objects.

    Storage-agnostic: Does not assume filesystem, database, or any specific backend.
    """

    @property
    @abstractmethod
    def eval_name(self) -> str:
        """Evaluation name (logical identifier)."""

    # Data sources for config artifacts
    @property
    @abstractmethod
    def eval_config(self) -> StructDataSource[EvalConfig]:
        """Evaluation configuration data source."""

    @property
    @abstractmethod
    def agents(self) -> StructDataSource[Dict]:
        """Agents and models configuration data source."""

    @property
    @abstractmethod
    def scenarios(self) -> RecordDataSource[Scenario]:
        """Test scenarios data source."""

    # Prompt template access
    @abstractmethod
    def get_prompt(self, prompt_ref: str) -> str:
        """
        Get prompt template content (cached).

        Args:
            prompt_ref: Prompt reference in format "name:version" or "name:latest"

        Returns:
            Prompt template text with {{variable}} placeholders

        Raises:
            ResourceNotFoundError: If prompt template or version not found
        """

    # Judge definition access
    @abstractmethod
    def get_judge(self, judge_name: str) -> Dict:
        """
        Get judge definition content (cached).

        Args:
            judge_name: Judge name

        Returns:
            Judge specification struct

        Raises:
            ResourceNotFoundError: If judge definition not found
        """


class RunContext(ABC):
    """
    Run execution context (Abstract Base Class).

    Provides read/write access to run-specific artifacts
    (results, metadata, reports, logs) through DataSource objects.

    Storage-agnostic: Does not assume filesystem, database, or any specific backend.
    """

    @property
    @abstractmethod
    def eval_ctx(self) -> EvalContext:
        """Access to evaluation configuration."""

    @property
    @abstractmethod
    def run_id(self) -> str:
        """Run identifier (logical identifier)."""

    # Artifact data sources
    @property
    @abstractmethod
    def results_raw(self) -> RecordDataSource:
        """Raw execution results data source."""

    @property
    @abstractmethod
    def results_judged(self) -> RecordDataSource:
        """Judged results data source."""

    @property
    @abstractmethod
    def telemetry(self) -> RecordDataSource:
        """Telemetry spans data source (REQUIRED - source of truth for metrics)."""

    @property
    @abstractmethod
    def run_metadata(self) -> StructDataSource:
        """Run metadata summary data source."""

    @property
    @abstractmethod
    def reports(self) -> MultiFormatDataSource:
        """Reports in multiple formats data source."""

    @property
    @abstractmethod
    def run_logger(self) -> logging.Logger:
        """Run-specific logger."""

    @abstractmethod
    def snapshot_run_config(self) -> None:
        """
        Copy eval configs to run storage for reproducibility.

        This ensures the exact configuration used for this run is preserved,
        even if the eval config is later modified.
        """


class LocalFileSystemEvalContext(EvalContext):
    """
    Local filesystem evaluation context implementation.

    Provides lazy-loaded DataSource objects for evaluation configuration.
    Steps access data by calling .read() on the data sources.

    Directory structure:
        .gavel/evaluations/{eval_name}/
        ├── config/
        │   ├── eval_config.json
        │   ├── agents.json
        │   ├── prompts/
        │   │   └── {name}.toml
        │   └── judges/
        │       └── {name}.json
        └── data/
            └── scenarios.json (or .csv)
    """

    def __init__(self, eval_name: str, eval_root: Path = Path(".gavel/evaluations")):
        """
        Initialize evaluation context.

        Args:
            eval_name: Name of the evaluation
            eval_root: Root directory for evaluations (default: .gavel/evaluations)
        """
        self._eval_name: str = eval_name
        self._eval_root: Path = eval_root

        # Initialize storage backend
        self._storage = LocalStorageBackend(self._eval_root / eval_name)

        # Lazy-loaded data sources
        self._eval_config_source: Optional[StructDataSource[EvalConfig]] = None
        self._agents_source: Optional[StructDataSource[Dict]] = None
        self._scenarios_source: Optional[RecordDataSource[Scenario]] = None

        # Caches
        self._prompt_cache: Dict[str, str] = {}
        self._judge_cache: Dict[str, Dict] = {}

    @property
    def eval_name(self) -> str:
        """Evaluation name."""
        return self._eval_name

    @property
    def eval_root(self) -> Path:
        """Evaluation root directory."""
        return self._eval_root

    @property
    def eval_dir(self) -> Path:
        """Evaluation directory path."""
        return self._eval_root / self._eval_name

    @property
    def config_dir(self) -> Path:
        """Configuration directory path."""
        return self.eval_dir / "config"

    @property
    def eval_config(self) -> StructDataSource[EvalConfig]:
        """
        Evaluation configuration data source (config/eval_config.json).

        Returns DataSource - steps must call .read() to get data.
        Lazy-loaded on first access.
        """
        if self._eval_config_source is None:
            self._eval_config_source = StructDataSource(
                self._storage, "config/eval_config.json", schema=EvalConfig
            )
        return self._eval_config_source

    @property
    def agents(self) -> StructDataSource[Dict]:
        """
        Agents configuration data source (config/agents.json).

        Returns DataSource - steps must call .read() to get data.
        Lazy-loaded on first access.
        """
        if self._agents_source is None:
            self._agents_source = StructDataSource(
                self._storage,
                "config/agents.json",
                schema=None,  # Use dict for now - can add AgentsConfig schema later
            )
        return self._agents_source

    @property
    def scenarios(self) -> RecordDataSource[Scenario]:
        """
        Scenarios data source (data/scenarios.json or .csv).

        Returns DataSource - steps can:
        - Call .read() to load all scenarios into memory
        - Call .iter() to stream scenarios one at a time
        Lazy-loaded on first access.
        """
        if self._scenarios_source is None:
            # Auto-detect format from file extension
            scenarios_path = "data/scenarios.json"
            if not (self.eval_dir / scenarios_path).exists():
                scenarios_path = "data/scenarios.csv"

            self._scenarios_source = RecordDataSource(
                self._storage, scenarios_path, schema=Scenario
            )
        return self._scenarios_source

    def get_prompt(self, prompt_ref: str) -> str:
        """
        Get prompt template content (cached).

        Args:
            prompt_ref: Prompt reference in format "name:version" or "name:latest"

        Returns:
            Prompt template text with {{variable}} placeholders

        Raises:
            ResourceNotFoundError: If prompt template or version not found
        """
        if prompt_ref not in self._prompt_cache:
            try:
                # Parse prompt_ref: "name:version"
                name, version = prompt_ref.split(":")

                # Read TOML file
                prompt_source = StructDataSource(self._storage, f"config/prompts/{name}.toml")
                prompt_data = prompt_source.read()  # dict

                # Get specific version or latest
                if version == "latest":
                    # Get highest version number
                    versions = [k for k in prompt_data.keys() if k.startswith("v")]
                    if not versions:
                        raise ResourceNotFoundError(
                            f"Prompt '{name}' has no versions - Check prompt file format"
                        )
                    version = max(versions, key=lambda v: int(v[1:]))

                if version not in prompt_data:
                    raise ResourceNotFoundError(
                        f"Version '{version}' not found in prompt '{name}' - "
                        f"Available versions: {list(prompt_data.keys())}"
                    )

                self._prompt_cache[prompt_ref] = prompt_data[version]

            except FileNotFoundError as e:
                raise ResourceNotFoundError(
                    f"Prompt template '{name}' not found - Check config/prompts/ directory"
                ) from e
            except (KeyError, ValueError) as e:
                raise ResourceNotFoundError(
                    f"Invalid prompt reference '{prompt_ref}' - Use format 'name:version'"
                ) from e

        return self._prompt_cache[prompt_ref]

    def get_judge(self, judge_name: str) -> Dict:
        """
        Get judge definition content (cached).

        Args:
            judge_name: Judge name

        Returns:
            Judge specification struct

        Raises:
            ResourceNotFoundError: If judge definition not found
        """
        if judge_name not in self._judge_cache:
            try:
                # Read JSON file
                judge_source = StructDataSource(self._storage, f"config/judges/{judge_name}.json")
                judge_data = judge_source.read()  # dict
                self._judge_cache[judge_name] = judge_data

            except FileNotFoundError as e:
                raise ResourceNotFoundError(
                    f"Judge definition '{judge_name}' not found - Check config/judges/ directory"
                ) from e

        return self._judge_cache[judge_name]


class LocalRunContext(RunContext):
    """
    Local filesystem run context implementation.

    Provides DataSource objects for run artifacts. Steps write data immediately
    to storage via the data sources.

    Directory structure:
        .gavel/runs/{run_id}/
        ├── .config/                    # Config snapshot for reproducibility
        │   ├── eval_config.json
        │   ├── agents.json
        │   └── scenarios.json
        ├── results_raw.jsonl           # OutputRecord records
        ├── results_judged.jsonl        # JudgedRecord records
        ├── telemetry.jsonl             # TelemetrySpan records
        ├── run_metadata.json           # RunMetadata summary
        ├── report.html                 # Primary report format
        └── run.log                     # Execution log
    """

    def __init__(
        self,
        eval_ctx: EvalContext,
        base_dir: Path = Path(".gavel/runs"),
        run_id: Optional[str] = None,
    ):
        """
        Initialize run context.

        Args:
            eval_ctx: Evaluation context with configuration
            base_dir: Base directory for runs (default: .gavel/runs)
            run_id: Run identifier (generated if not provided)
        """
        # Reference to eval context
        self._eval_ctx = eval_ctx

        # Generate run_id if not provided
        if run_id is None:
            run_id = f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        self._run_id = run_id
        self._base_dir = base_dir

        # Initialize storage backend
        self._storage = LocalStorageBackend(base_dir)

        # Initialize all artifact data sources
        self._init_artifacts()

        # Configure run-specific logger
        self._configure_logger()

        # Snapshot eval config for reproducibility
        self.snapshot_run_config()

    @property
    def eval_ctx(self) -> LocalFileSystemEvalContext:
        """Access to evaluation configuration."""
        return self._eval_ctx

    @property
    def run_id(self) -> str:
        """Run identifier."""
        return self._run_id

    @property
    def run_dir(self) -> Path:
        """Run directory path."""
        return self._base_dir / self._run_id

    def _init_artifacts(self) -> None:
        """
        Initialize artifact data sources for local filesystem storage.

        Each artifact is exposed as a DataSource property that steps
        can write to immediately.
        """
        # Import schemas - avoid circular imports
        from gavel_ai.core.models import OutputRecord

        # Raw results - JSONL with schema validation
        self._results_raw = RecordDataSource(
            self._storage, f"{self._run_id}/results_raw.jsonl", schema=OutputRecord
        )

        # Judged results - JSONL (no schema validation for now)
        self._results_judged = RecordDataSource(
            self._storage,
            f"{self._run_id}/results_judged.jsonl",
            schema=None,  # Use dict for now
        )

        # Telemetry - JSONL (no schema validation for now)
        self._telemetry = RecordDataSource(
            self._storage,
            f"{self._run_id}/telemetry.jsonl",
            schema=None,  # Use dict for now
        )

        # Run metadata - JSON (no schema validation for now)
        self._run_metadata = StructDataSource(
            self._storage,
            f"{self._run_id}/run_metadata.json",
            schema=None,  # Use dict for now
        )

        # Reports - multiple formats (html, md, pdf)
        self._reports = MultiFormatDataSource(
            self._storage,
            f"{self._run_id}",  # Base directory
            "report",  # Base filename
        )

    def _configure_logger(self) -> None:
        """Configure run-specific logger for local filesystem."""
        log_file = self._base_dir / self._run_id / "run.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Create rotating file handler
        handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s")
        )

        # Create run-specific logger
        self._run_logger = logging.getLogger(f"gavel_ai.{self._run_id}")
        self._run_logger.addHandler(handler)
        self._run_logger.setLevel(logging.INFO)
        self._run_logger.propagate = False

    def snapshot_run_config(self) -> None:
        """
        Copy eval configs to .config/ subdirectory for reproducibility.

        This ensures the exact configuration used for this run is preserved,
        even if the eval config is later modified.
        """
        config_snapshot_dir = f"{self._run_id}/.config"

        # Copy eval_config.json
        eval_config_content = self._eval_ctx.eval_config.read()
        eval_config_snapshot = StructDataSource(
            self._storage,
            f"{config_snapshot_dir}/eval_config.json",
        )
        eval_config_snapshot.write(eval_config_content)

        # Copy agents.json
        agents_content = self._eval_ctx.agents.read()
        agents_snapshot = StructDataSource(
            self._storage,
            f"{config_snapshot_dir}/agents.json",
        )
        agents_snapshot.write(agents_content)

        # Copy scenarios
        scenarios_content = self._eval_ctx.scenarios.read()
        scenarios_snapshot = RecordDataSource(
            self._storage,
            f"{config_snapshot_dir}/scenarios.json",
        )
        scenarios_snapshot.write(scenarios_content)

    # Artifact properties - expose DataSources to steps
    @property
    def results_raw(self) -> RecordDataSource:
        """
        Raw execution results data source.

        Steps write results via: run_ctx.results_raw.append(record)
        """
        return self._results_raw

    @property
    def results_judged(self) -> RecordDataSource:
        """
        Judged results data source.

        Steps write results via: run_ctx.results_judged.append(record)
        """
        return self._results_judged

    @property
    def telemetry(self) -> RecordDataSource:
        """
        Telemetry spans data source (REQUIRED - source of truth for metrics).

        Steps write spans via: run_ctx.telemetry.append(span)
        """
        return self._telemetry

    @property
    def run_metadata(self) -> StructDataSource:
        """
        Run metadata summary data source.

        Reporter writes metadata via: run_ctx.run_metadata.write(metadata)
        """
        return self._run_metadata

    @property
    def reports(self) -> MultiFormatDataSource:
        """
        Reports in multiple formats data source.

        Reporter writes via: run_ctx.reports.write(html, "html")
        """
        return self._reports

    @property
    def run_logger(self) -> logging.Logger:
        """
        Run-specific logger configured with file handler.

        Steps use for logging: run_ctx.run_logger.info("message")
        """
        return self._run_logger


__all__ = [
    # Abstract base classes
    "EvalContext",
    "RunContext",
    # Concrete implementations
    "LocalFileSystemEvalContext",
    "LocalRunContext",
]
