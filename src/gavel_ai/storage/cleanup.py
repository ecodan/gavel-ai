"""
Run cleanup utilities for disk space management.

Provides RunCleaner for deleting old runs while preserving milestones.

Per Story 6.6: Enable disk space management with milestone protection.
"""

import json
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Union


class RunCleaner:
    """
    Clean up old runs to manage disk space.

    Always preserves milestone runs regardless of age.
    """

    def __init__(self, base_dir: str = ".gavel"):
        """
        Initialize run cleaner.

        Args:
            base_dir: Base directory for .gavel storage (default: ".gavel")
        """
        self.base_dir = Path(base_dir)

    def parse_time_expression(self, expr: str) -> int:
        """
        Parse time expression into days.

        Supports formats: "30d", "7d", "1w", "2m", "1y"
        - d = days
        - w = weeks
        - m = months (30 days)
        - y = years (365 days)

        Args:
            expr: Time expression string (e.g., "30d", "1w", "2m")

        Returns:
            int: Number of days

        Raises:
            ValueError: If expression format is invalid

        Example:
            >>> cleaner = RunCleaner()
            >>> cleaner.parse_time_expression("30d")
            30
            >>> cleaner.parse_time_expression("2w")
            14
        """
        # Match pattern: number followed by unit
        match = re.match(r"^(\d+)([dwmy])$", expr.lower())
        if not match:
            raise ValueError(
                f"Invalid time expression: '{expr}'. Use format like '30d', '1w', '2m', '1y'"
            )

        value = int(match.group(1))
        unit = match.group(2)

        # Convert to days
        multipliers = {"d": 1, "w": 7, "m": 30, "y": 365}

        return value * multipliers[unit]

    async def cleanup_runs(
        self,
        older_than: Union[int, str],
        eval_name: Optional[str] = None,
        dry_run: bool = True,
    ) -> List[str]:
        """
        Delete runs older than specified time (preserving milestones).

        Args:
            older_than: Delete runs older than this threshold.
                       Can be integer (days) or string expression ("30d", "1w", "2m", "1y")
            eval_name: Only clean up runs for specific evaluation (optional)
            dry_run: If True, only report what would be deleted (default: True)

        Returns:
            List of run IDs that were (or would be) deleted

        Example:
            >>> cleaner = RunCleaner()
            >>> deleted = await cleaner.cleanup_runs(older_than="30d", dry_run=False)
            >>> print(f"Deleted {len(deleted)} old runs")
            >>> deleted = await cleaner.cleanup_runs(older_than=30, dry_run=False)
        """
        # Parse time expression if string, otherwise use integer directly
        if isinstance(older_than, str):
            older_than_days = self.parse_time_expression(older_than)
        else:
            older_than_days = older_than

        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        deleted_runs: List[str] = []

        # Pattern: .gavel/evaluations/*/runs/*
        if eval_name:
            run_dirs = self.base_dir.glob(f"evaluations/{eval_name}/runs/*")
        else:
            run_dirs = self.base_dir.glob("evaluations/*/runs/*")

        for run_dir in run_dirs:
            if not run_dir.is_dir():
                continue

            manifest_path = run_dir / "manifest.json"
            if not manifest_path.exists():
                continue

            try:
                with open(manifest_path) as f:
                    manifest = json.load(f)

                # Check if milestone - NEVER delete milestones
                if manifest.get("is_milestone", False):
                    continue

                # Parse timestamp
                timestamp_str = manifest.get("timestamp")
                if not timestamp_str:
                    continue

                timestamp = datetime.fromisoformat(timestamp_str)

                # Check if older than cutoff
                if timestamp < cutoff_date:
                    run_id = run_dir.name

                    if not dry_run:
                        # Actually delete the run directory
                        shutil.rmtree(run_dir)

                    deleted_runs.append(run_id)

            except (json.JSONDecodeError, ValueError, KeyError):
                # Skip corrupted manifests
                continue

        return deleted_runs
