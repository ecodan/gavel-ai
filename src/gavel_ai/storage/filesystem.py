"""
Filesystem-based storage implementation.

Implements LocalFilesystemRun for v1 artifact storage using local filesystem
with human-readable JSON/JSONL files for git-friendliness.

Per Architecture Decision 8: Domain-driven storage abstraction.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from gavel_ai.core.exceptions import StorageError
from gavel_ai.models.runtime import ArtifactRef
from gavel_ai.storage.base import Run


class LocalFilesystemRun(Run):
    """
    Filesystem-based Run implementation.

    Per Architecture Decision 8: v1 storage uses local filesystem
    with human-readable artifacts for git-friendliness.

    Directory structure: .gavel/evaluations/<eval-name>/runs/run-<timestamp>/

    Artifacts:
    - manifest.json: Run manifest with version, timestamps, config hash
    - config/: Configuration files (eval_config.json, agents.json, etc.)
    - telemetry.jsonl: Telemetry events (one JSON object per line)
    - results.jsonl: Evaluation results (one JSON object per line)
    - run_metadata.json: Run metadata (duration, status, etc.)
    - gavel.log: Execution logs
    - report.html: Generated HTML report
    """

    def __init__(
        self,
        run_id: str,
        eval_name: str,
        metadata: Dict[str, Any],
        base_dir: str = ".gavel",
    ):
        """
        Initialize filesystem run.

        Args:
            run_id: Unique run identifier (e.g., "run-20251230-120000")
            eval_name: Evaluation name for directory organization
            metadata: Run metadata dict
            base_dir: Base directory for .gavel storage (default: ".gavel")
        """
        super().__init__(run_id, metadata)
        self.eval_name = eval_name
        self.base_dir = Path(base_dir)
        self.run_dir = self.base_dir / "evaluations" / eval_name / "runs" / run_id
        self._artifacts: Dict[str, ArtifactRef] = {}

        # Data attributes for artifacts (set before save, populated after load)
        self.manifest_data: Optional[Dict[str, Any]] = None
        self.config_data: Optional[Dict[str, Any]] = None
        self.telemetry_data: Optional[List[Dict[str, Any]]] = None
        self.results_data: Optional[List[Dict[str, Any]]] = None
        self.metadata_data: Optional[Dict[str, Any]] = None
        self.log_data: Optional[str] = None
        self.report_data: Optional[str] = None

    async def save(self) -> str:
        """
        Save run to filesystem.

        Creates directory structure and persists all artifacts.

        Returns:
            str: Path to run directory

        Raises:
            StorageError: On directory creation or save failures
        """
        try:
            # Create directory structure
            self.run_dir.mkdir(parents=True, exist_ok=True)
            (self.run_dir / "config").mkdir(exist_ok=True)

            # Save all artifacts (only if data is set)
            if self.manifest_data is not None:
                await self.save_manifest()
            if self.config_data is not None:
                await self.save_config()
            if self.telemetry_data is not None:
                await self.save_telemetry()
            if self.results_data is not None:
                await self.save_results()
            if self.metadata_data is not None:
                await self.save_metadata()
            if self.log_data is not None:
                await self.save_log()
            if self.report_data is not None:
                await self.save_report()

            return str(self.run_dir)

        except (OSError, PermissionError) as e:
            raise StorageError(f"StorageError: Failed to save run {self.run_id} - {e}") from e

    @staticmethod
    async def load(run_id: str, base_dir: str = ".gavel") -> "LocalFilesystemRun":
        """
        Load run from filesystem by ID.

        Args:
            run_id: Run identifier to load
            base_dir: Base directory for .gavel storage

        Returns:
            LocalFilesystemRun: Loaded run instance

        Raises:
            StorageError: If run not found or load fails
        """
        # Find run directory by searching evaluations
        base_path = Path(base_dir)
        eval_dirs = list(base_path.glob(f"evaluations/*/runs/{run_id}"))

        if not eval_dirs:
            raise StorageError(f"StorageError: Run {run_id} not found - Check run ID")

        run_dir = eval_dirs[0]

        # Extract eval_name from path
        eval_name = run_dir.parent.parent.name

        # Load metadata first to reconstruct run
        try:
            metadata = await LocalFilesystemRun._load_metadata_file(run_dir)
        except Exception as e:
            raise StorageError(
                f"StorageError: Failed to load metadata for run {run_id} - {e}"
            ) from e

        # Create run instance
        run = LocalFilesystemRun(run_id, eval_name, metadata, base_dir)

        # Load all artifacts (if they exist)
        try:
            if (run_dir / "manifest.json").exists():
                await run.load_manifest()
            if (run_dir / "config").exists():
                await run.load_config()
            if (run_dir / "telemetry.jsonl").exists():
                await run.load_telemetry()
            if (run_dir / "results.jsonl").exists():
                await run.load_results()
            if (run_dir / "run_metadata.json").exists():
                await run.load_metadata()
            if (run_dir / "gavel.log").exists():
                await run.load_log()
            if (run_dir / "report.html").exists():
                await run.load_report()
        except Exception as e:
            raise StorageError(
                f"StorageError: Failed to load artifacts for run {run_id} - {e}"
            ) from e

        return run

    @staticmethod
    async def _load_metadata_file(run_dir: Path) -> Dict[str, Any]:
        """
        Load run constructor metadata from manifest.json.

        Args:
            run_dir: Run directory path

        Returns:
            Dict containing Run constructor metadata

        Raises:
            Exception: On load failures
        """
        # Try manifest.json first (contains run metadata)
        manifest_path = run_dir / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)
                # Return the metadata stored in manifest, or extract from manifest itself
                return manifest.get("metadata", {})
        return {}

    async def mark_milestone(self, comment: str) -> None:
        """
        Mark this run as a milestone.

        Per Story 6.5: Milestone runs are protected from cleanup and
        preserved for baseline/production tracking.

        Args:
            comment: Explanation of why this is a milestone

        Raises:
            StorageError: If manifest update fails

        Example:
            >>> run = await LocalFilesystemRun.load("run-123")
            >>> await run.mark_milestone("Baseline for v1.0")
        """
        from datetime import datetime

        try:
            # Load current manifest if not already loaded
            if self.manifest_data is None:
                await self.load_manifest()

            # Update manifest with milestone fields
            if self.manifest_data is None:
                self.manifest_data = {}

            self.manifest_data["is_milestone"] = True
            self.manifest_data["milestone_comment"] = comment
            self.manifest_data["milestone_timestamp"] = datetime.now().isoformat()

            # Save updated manifest
            await self.save_manifest()

        except Exception as e:
            raise StorageError(
                f"StorageError: Failed to mark run {self.run_id} as milestone - {e}"
            ) from e

    @property
    def artifacts(self) -> Dict[str, ArtifactRef]:
        """
        Get dictionary of run artifacts.

        Returns:
            Dict mapping artifact names to ArtifactRef instances
        """
        return self._artifacts

    # Individual artifact save methods

    async def save_manifest(self) -> None:
        """Save manifest.json artifact."""
        if self.manifest_data is None:
            self.manifest_data = {}

        # Include constructor metadata in manifest for reconstruction
        manifest_with_metadata = {
            **self.manifest_data,
            "metadata": self.metadata,  # Store constructor metadata
        }

        manifest_path = self.run_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest_with_metadata, f, indent=2)

        self._artifacts["manifest"] = ArtifactRef(
            path=str(manifest_path), type="json", size=manifest_path.stat().st_size
        )

    async def save_config(self) -> None:
        """Save config/ directory artifacts."""
        if self.config_data is None:
            return

        config_dir = self.run_dir / "config"

        # Save each config file separately
        for config_name, config_content in self.config_data.items():
            config_path = config_dir / f"{config_name}.json"
            with open(config_path, "w") as f:
                json.dump(config_content, f, indent=2)

            self._artifacts[f"config_{config_name}"] = ArtifactRef(
                path=str(config_path), type="json", size=config_path.stat().st_size
            )

    async def save_telemetry(self) -> None:
        """Save telemetry.jsonl artifact."""
        if self.telemetry_data is None:
            return

        telemetry_path = self.run_dir / "telemetry.jsonl"
        with open(telemetry_path, "w") as f:
            for event in self.telemetry_data:
                f.write(json.dumps(event) + "\n")

        self._artifacts["telemetry"] = ArtifactRef(
            path=str(telemetry_path),
            type="jsonl",
            size=telemetry_path.stat().st_size,
        )

    async def save_results(self) -> None:
        """Save results.jsonl artifact."""
        if self.results_data is None:
            return

        results_path = self.run_dir / "results.jsonl"
        with open(results_path, "w") as f:
            for result in self.results_data:
                f.write(json.dumps(result) + "\n")

        self._artifacts["results"] = ArtifactRef(
            path=str(results_path), type="jsonl", size=results_path.stat().st_size
        )

    async def save_metadata(self) -> None:
        """Save run_metadata.json artifact."""
        if self.metadata_data is None:
            return

        metadata_path = self.run_dir / "run_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(self.metadata_data, f, indent=2)

        self._artifacts["metadata"] = ArtifactRef(
            path=str(metadata_path), type="json", size=metadata_path.stat().st_size
        )

    async def save_log(self) -> None:
        """Save gavel.log artifact."""
        if self.log_data is None:
            return

        log_path = self.run_dir / "gavel.log"
        with open(log_path, "w") as f:
            f.write(self.log_data)

        self._artifacts["log"] = ArtifactRef(
            path=str(log_path), type="log", size=log_path.stat().st_size
        )

    async def save_report(self) -> None:
        """Save report.html artifact."""
        if self.report_data is None:
            return

        report_path = self.run_dir / "report.html"
        with open(report_path, "w") as f:
            f.write(self.report_data)

        self._artifacts["report"] = ArtifactRef(
            path=str(report_path), type="html", size=report_path.stat().st_size
        )

    # Individual artifact load methods

    async def load_manifest(self) -> None:
        """Load manifest.json artifact."""
        manifest_path = self.run_dir / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                full_manifest = json.load(f)

            # Separate constructor metadata from manifest data
            self.manifest_data = {k: v for k, v in full_manifest.items() if k != "metadata"}

            self._artifacts["manifest"] = ArtifactRef(
                path=str(manifest_path), type="json", size=manifest_path.stat().st_size
            )

    async def load_config(self) -> None:
        """Load config/ directory artifacts."""
        config_dir = self.run_dir / "config"
        if not config_dir.exists():
            return

        self.config_data = {}

        # Load all JSON files in config directory
        for config_path in config_dir.glob("*.json"):
            config_name = config_path.stem
            with open(config_path) as f:
                self.config_data[config_name] = json.load(f)

            self._artifacts[f"config_{config_name}"] = ArtifactRef(
                path=str(config_path), type="json", size=config_path.stat().st_size
            )

    async def load_telemetry(self) -> None:
        """Load telemetry.jsonl artifact."""
        telemetry_path = self.run_dir / "telemetry.jsonl"
        if telemetry_path.exists():
            self.telemetry_data = []
            with open(telemetry_path) as f:
                for line in f:
                    self.telemetry_data.append(json.loads(line.strip()))

            self._artifacts["telemetry"] = ArtifactRef(
                path=str(telemetry_path),
                type="jsonl",
                size=telemetry_path.stat().st_size,
            )

    async def load_results(self) -> None:
        """Load results.jsonl artifact."""
        results_path = self.run_dir / "results.jsonl"
        if results_path.exists():
            self.results_data = []
            with open(results_path) as f:
                for line in f:
                    self.results_data.append(json.loads(line.strip()))

            self._artifacts["results"] = ArtifactRef(
                path=str(results_path), type="jsonl", size=results_path.stat().st_size
            )

    async def load_metadata(self) -> None:
        """Load run_metadata.json artifact."""
        metadata_path = self.run_dir / "run_metadata.json"
        if metadata_path.exists():
            with open(metadata_path) as f:
                self.metadata_data = json.load(f)

            self._artifacts["metadata"] = ArtifactRef(
                path=str(metadata_path), type="json", size=metadata_path.stat().st_size
            )

    async def load_log(self) -> None:
        """Load gavel.log artifact."""
        log_path = self.run_dir / "gavel.log"
        if log_path.exists():
            with open(log_path) as f:
                self.log_data = f.read()

            self._artifacts["log"] = ArtifactRef(
                path=str(log_path), type="log", size=log_path.stat().st_size
            )

    async def load_report(self) -> None:
        """Load report.html artifact."""
        report_path = self.run_dir / "report.html"
        if report_path.exists():
            with open(report_path) as f:
                self.report_data = f.read()

            self._artifacts["report"] = ArtifactRef(
                path=str(report_path), type="html", size=report_path.stat().st_size
            )
