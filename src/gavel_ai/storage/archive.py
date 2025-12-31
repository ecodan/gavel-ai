"""
Run archive and export utilities.

Provides RunArchiver for exporting/importing runs as ZIP files.

Per Story 6.7: Enable run portability and sharing via ZIP archives.
"""

import zipfile
from pathlib import Path
from typing import Optional

from gavel_ai.core.exceptions import StorageError


class RunArchiver:
    """
    Archive and export runs as ZIP files.

    Enables run portability for sharing and backup.
    """

    def __init__(self, base_dir: str = ".gavel"):
        """
        Initialize run archiver.

        Args:
            base_dir: Base directory for .gavel storage (default: ".gavel")
        """
        self.base_dir = Path(base_dir)

    async def export_run(
        self, run_id: str, output_path: str, eval_name: Optional[str] = None
    ) -> str:
        """
        Export run to ZIP file.

        Args:
            run_id: Run identifier to export
            output_path: Path for output ZIP file
            eval_name: Evaluation name (optional, auto-detected if not provided)

        Returns:
            str: Path to created ZIP file

        Raises:
            StorageError: If run not found or export fails

        Example:
            >>> archiver = RunArchiver()
            >>> zip_path = await archiver.export_run("run-123", "run-123.zip")
        """
        # Find run directory
        if eval_name:
            run_dir = self.base_dir / "evaluations" / eval_name / "runs" / run_id
        else:
            # Search for run across all evaluations
            run_dirs = list(self.base_dir.glob(f"evaluations/*/runs/{run_id}"))
            if not run_dirs:
                raise StorageError(
                    f"StorageError: Run {run_id} not found - Check run ID"
                )
            run_dir = run_dirs[0]

        if not run_dir.exists():
            raise StorageError(f"StorageError: Run {run_id} not found - Check run ID")

        try:
            # Create ZIP archive
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Add all files in run directory
                for file_path in run_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(run_dir.parent.parent.parent)
                        zipf.write(file_path, arcname)

            return output_path

        except Exception as e:
            raise StorageError(
                f"StorageError: Failed to export run {run_id} - {e}"
            ) from e

    async def import_run(self, zip_path: str) -> str:
        """
        Import run from ZIP file.

        Args:
            zip_path: Path to ZIP file to import

        Returns:
            str: Imported run ID

        Raises:
            StorageError: If import fails

        Example:
            >>> archiver = RunArchiver()
            >>> run_id = await archiver.import_run("run-123.zip")
        """
        try:
            with zipfile.ZipFile(zip_path, "r") as zipf:
                # Extract to base_dir
                zipf.extractall(self.base_dir)

                # Get run_id from extracted paths
                # Pattern: evaluations/<eval-name>/runs/<run-id>/
                for name in zipf.namelist():
                    parts = Path(name).parts
                    if len(parts) >= 4 and parts[0] == "evaluations" and parts[2] == "runs":
                        run_id = parts[3]
                        return run_id

                raise StorageError(
                    "StorageError: Invalid run archive - No run directory found in ZIP"
                )

        except zipfile.BadZipFile as e:
            raise StorageError(f"StorageError: Invalid ZIP file - {e}") from e
        except Exception as e:
            raise StorageError(f"StorageError: Failed to import run - {e}") from e
