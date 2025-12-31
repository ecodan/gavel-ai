"""
RunContext API for programmatic run access.

Provides RunContext wrapper for notebook-friendly SDK-style access to runs.

Per Story 6.8: Enable custom analysis and programmatic run access.
"""

from pathlib import Path
from typing import Any, Dict, List

from gavel_ai.core.exceptions import StorageError
from gavel_ai.core.models import Manifest
from gavel_ai.storage.filesystem import LocalFilesystemRun


class RunContext:
    """
    Convenience wrapper for programmatic run access.

    Provides SDK-style methods for analyzing runs in notebooks or scripts.

    Example:
        >>> ctx = await RunContext.load("run-20251230-120000")
        >>> results = ctx.get_results()
        >>> print(f"Processed {len(results)} scenarios")
        >>> manifest = ctx.get_manifest()
        >>> print(f"Status: {manifest.status}")
    """

    def __init__(self, run: LocalFilesystemRun):
        """
        Initialize run context.

        Args:
            run: Loaded LocalFilesystemRun instance
        """
        self.run = run

    @classmethod
    async def load(cls, run_id: str, base_dir: str = ".gavel") -> "RunContext":
        """
        Load run by ID and return context wrapper.

        Args:
            run_id: Run identifier to load
            base_dir: Base directory for .gavel storage (default: ".gavel")

        Returns:
            RunContext: Wrapper for programmatic access

        Raises:
            StorageError: If run not found

        Example:
            >>> ctx = await RunContext.load("run-20251230-120000")
        """
        run = await LocalFilesystemRun.load(run_id, base_dir)
        return cls(run)

    def get_manifest(self) -> Manifest:
        """
        Get run manifest as Manifest model.

        Returns:
            Manifest: Parsed manifest with metadata

        Example:
            >>> manifest = ctx.get_manifest()
            >>> print(manifest.status)
            'completed'
        """
        if not self.run.manifest_data:
            raise StorageError("StorageError: Manifest not loaded - Load run first")

        return Manifest(**self.run.manifest_data)

    def get_results(self) -> List[Dict[str, Any]]:
        """
        Get evaluation results.

        Returns:
            List of result dictionaries

        Example:
            >>> results = ctx.get_results()
            >>> avg_score = sum(r["score"] for r in results) / len(results)
        """
        if not self.run.results_data:
            return []
        return self.run.results_data

    def get_telemetry(self) -> List[Dict[str, Any]]:
        """
        Get telemetry events.

        Returns:
            List of telemetry event dictionaries

        Example:
            >>> events = ctx.get_telemetry()
            >>> errors = [e for e in events if e.get("level") == "error"]
        """
        if not self.run.telemetry_data:
            return []
        return self.run.telemetry_data

    def get_config(self) -> Dict[str, Any]:
        """
        Get run configuration.

        Returns:
            Configuration dictionary

        Example:
            >>> config = ctx.get_config()
            >>> print(config["eval_config"]["name"])
        """
        if not self.run.config_data:
            return {}
        return self.run.config_data

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get run metadata.

        Returns:
            Metadata dictionary

        Example:
            >>> metadata = ctx.get_metadata()
            >>> duration = metadata.get("duration", 0)
        """
        if not self.run.metadata_data:
            return {}
        return self.run.metadata_data

    def get_log(self) -> str:
        """
        Get run log.

        Returns:
            Log content as string

        Example:
            >>> log = ctx.get_log()
            >>> errors = [line for line in log.split("\\n") if "ERROR" in line]
        """
        if not self.run.log_data:
            return ""
        return self.run.log_data

    def get_report(self) -> str:
        """
        Get generated report.

        Returns:
            Report HTML content

        Example:
            >>> report = ctx.get_report()
            >>> with open("report.html", "w") as f:
            ...     f.write(report)
        """
        if not self.run.report_data:
            return ""
        return self.run.report_data

    @property
    def run_id(self) -> str:
        """Get run ID."""
        return self.run.run_id

    @property
    def eval_name(self) -> str:
        """Get evaluation name."""
        return self.run.eval_name

    @property
    def run_dir(self) -> Path:
        """Get run directory path."""
        return self.run.run_dir
