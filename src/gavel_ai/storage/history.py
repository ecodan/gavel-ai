"""
Run history tracking and querying.

Provides RunHistory class for listing and filtering completed runs
across all evaluations.

Per FR-3.4 and FR-7.6: Enable run tracking and comparison over time.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class RunHistory:
    """
    Track and query run history.

    Scans filesystem for completed runs and provides filtering,
    pagination, and summary capabilities.
    """

    def __init__(self, base_dir: str = ".gavel"):
        """
        Initialize run history tracker.

        Args:
            base_dir: Base directory for .gavel storage (default: ".gavel")
        """
        self.base_dir = Path(base_dir)

    async def list_runs(
        self,
        eval_name: Optional[str] = None,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List runs with optional filters and pagination.

        Args:
            eval_name: Filter by evaluation name (optional)
            after: Filter runs after this timestamp (optional)
            before: Filter runs before this timestamp (optional)
            limit: Maximum number of runs to return (default: 100)
            offset: Number of runs to skip (default: 0)

        Returns:
            List of run summaries with fields:
            - run_id: Run identifier
            - eval_name: Evaluation name
            - timestamp: Run start time (ISO 8601)
            - scenario_count: Number of scenarios
            - variant_count: Number of variants
            - status: Run completion status

        Example:
            >>> history = RunHistory()
            >>> runs = await history.list_runs(eval_name="test", limit=10)
            >>> len(runs)
            10
        """
        # Scan for all run directories
        runs: List[Dict[str, Any]] = []

        # Pattern: .gavel/evaluations/*/runs/*
        if eval_name:
            # Only scan specific evaluation
            run_dirs = self.base_dir.glob(f"evaluations/{eval_name}/runs/*")
        else:
            # Scan all evaluations
            run_dirs = self.base_dir.glob("evaluations/*/runs/*")

        # Load manifest from each run
        for run_dir in run_dirs:
            if not run_dir.is_dir():
                continue

            manifest_path = run_dir / "manifest.json"
            if not manifest_path.exists():
                # Skip runs without manifests
                continue

            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)

                # Extract eval_name from path
                run_eval_name = run_dir.parent.parent.name
                run_id = run_dir.name

                # Parse timestamp for filtering
                timestamp_str = manifest.get("timestamp")
                if timestamp_str:
                    # Handle both string timestamps and nested metadata
                    if isinstance(timestamp_str, dict):
                        # Skip if timestamp is malformed
                        continue
                    timestamp = datetime.fromisoformat(timestamp_str)
                else:
                    # Skip runs without timestamps
                    continue

                # Apply date filters
                if after and timestamp <= after:
                    continue
                if before and timestamp >= before:
                    continue

                # Build summary
                summary = {
                    "run_id": run_id,
                    "eval_name": run_eval_name,
                    "timestamp": timestamp_str,
                    "scenario_count": manifest.get("scenario_count", 0),
                    "variant_count": manifest.get("variant_count", 0),
                    "status": manifest.get("status", "unknown"),
                }

                runs.append(summary)

            except (json.JSONDecodeError, ValueError, KeyError):
                # Skip corrupted manifests
                continue

        # Sort by timestamp descending (newest first)
        runs.sort(key=lambda r: r["timestamp"], reverse=True)

        # Apply pagination
        paginated_runs = runs[offset : offset + limit]

        return paginated_runs
