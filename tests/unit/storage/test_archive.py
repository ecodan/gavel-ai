import pytest

pytestmark = pytest.mark.unit
"""
Unit tests for RunArchiver.
"""

import json
import zipfile
from pathlib import Path

import pytest

from gavel_ai.core.exceptions import StorageError
from gavel_ai.storage.archive import RunArchiver


class TestRunArchiver:
    """Test RunArchiver class."""

    def test_init_default_base_dir(self):
        """RunArchiver initializes with default base_dir."""
        archiver = RunArchiver()
        assert archiver.base_dir == Path(".gavel")

    def test_init_custom_base_dir(self):
        """RunArchiver initializes with custom base_dir."""
        archiver = RunArchiver(base_dir="/custom/path")
        assert archiver.base_dir == Path("/custom/path")

    @pytest.mark.asyncio
    async def test_export_run_with_eval_name(self, tmp_path: Path):
        """export_run creates ZIP file with eval_name specified."""
        # Setup run directory structure
        run_dir = tmp_path / "evaluations" / "test-eval" / "runs" / "run-123"
        run_dir.mkdir(parents=True)

        # Create some test files
        (run_dir / "manifest.json").write_text(json.dumps({"run_id": "run-123"}))
        (run_dir / "results.jsonl").write_text('{"test": "data"}\n')

        archiver = RunArchiver(base_dir=str(tmp_path))
        output_path = str(tmp_path / "export.zip")

        zip_path = await archiver.export_run(
            run_id="run-123", output_path=output_path, eval_name="test-eval"
        )

        assert zip_path == output_path
        assert Path(zip_path).exists()

        # Verify ZIP contents
        with zipfile.ZipFile(zip_path, "r") as zipf:
            names = zipf.namelist()
            assert any("manifest.json" in name for name in names)
            assert any("results.jsonl" in name for name in names)

    @pytest.mark.asyncio
    async def test_export_run_without_eval_name_searches(self, tmp_path: Path):
        """export_run searches all evaluations when eval_name not specified."""
        # Setup run in unknown evaluation
        run_dir = tmp_path / "evaluations" / "some-eval" / "runs" / "run-123"
        run_dir.mkdir(parents=True)
        (run_dir / "manifest.json").write_text(json.dumps({"run_id": "run-123"}))

        archiver = RunArchiver(base_dir=str(tmp_path))
        output_path = str(tmp_path / "export.zip")

        zip_path = await archiver.export_run(run_id="run-123", output_path=output_path)

        assert zip_path == output_path
        assert Path(zip_path).exists()

    @pytest.mark.asyncio
    async def test_export_run_raises_storage_error_if_not_found(self, tmp_path: Path):
        """export_run raises StorageError if run not found."""
        archiver = RunArchiver(base_dir=str(tmp_path))
        output_path = str(tmp_path / "export.zip")

        with pytest.raises(StorageError, match="Run nonexistent not found"):
            await archiver.export_run(
                run_id="nonexistent", output_path=output_path, eval_name="test"
            )

    @pytest.mark.asyncio
    async def test_export_run_includes_all_files_recursively(self, tmp_path: Path):
        """export_run includes all files in run directory recursively."""
        run_dir = tmp_path / "evaluations" / "test" / "runs" / "run-123"
        run_dir.mkdir(parents=True)

        # Create nested structure
        (run_dir / "manifest.json").write_text("{}")
        (run_dir / "config").mkdir()
        (run_dir / "config" / "agents.json").write_text("{}")
        (run_dir / "artifacts").mkdir()
        (run_dir / "artifacts" / "data.txt").write_text("test")

        archiver = RunArchiver(base_dir=str(tmp_path))
        output_path = str(tmp_path / "export.zip")

        await archiver.export_run(run_id="run-123", output_path=output_path)

        with zipfile.ZipFile(output_path, "r") as zipf:
            names = zipf.namelist()
            assert any("manifest.json" in name for name in names)
            assert any("agents.json" in name for name in names)
            assert any("data.txt" in name for name in names)

    @pytest.mark.asyncio
    async def test_export_run_preserves_directory_structure(self, tmp_path: Path):
        """export_run preserves directory structure in ZIP."""
        run_dir = tmp_path / "evaluations" / "test" / "runs" / "run-123"
        run_dir.mkdir(parents=True)
        (run_dir / "manifest.json").write_text("{}")

        archiver = RunArchiver(base_dir=str(tmp_path))
        output_path = str(tmp_path / "export.zip")

        await archiver.export_run(run_id="run-123", output_path=output_path)

        with zipfile.ZipFile(output_path, "r") as zipf:
            # Should have evaluation/runs structure
            assert any("test/runs/run-123" in name for name in zipf.namelist())

    @pytest.mark.asyncio
    async def test_import_run_extracts_to_base_dir(self, tmp_path: Path):
        """import_run extracts ZIP to base_dir."""
        # Create a ZIP archive
        zip_path = tmp_path / "import.zip"
        with zipfile.ZipFile(zip_path, "w") as zipf:
            zipf.writestr("evaluations/test/runs/run-456/manifest.json", "{}")

        archiver = RunArchiver(base_dir=str(tmp_path / "extracted"))

        run_id = await archiver.import_run(str(zip_path))

        assert run_id == "run-456"
        manifest_path = (
            tmp_path / "extracted" / "evaluations" / "test" / "runs" / "run-456" / "manifest.json"
        )
        assert manifest_path.exists()

    @pytest.mark.asyncio
    async def test_import_run_returns_run_id(self, tmp_path: Path):
        """import_run returns extracted run_id."""
        zip_path = tmp_path / "import.zip"
        with zipfile.ZipFile(zip_path, "w") as zipf:
            zipf.writestr("evaluations/eval-name/runs/run-999/manifest.json", "{}")

        archiver = RunArchiver(base_dir=str(tmp_path / "extracted"))

        run_id = await archiver.import_run(str(zip_path))

        assert run_id == "run-999"

    @pytest.mark.asyncio
    async def test_import_run_raises_storage_error_on_bad_zip(self, tmp_path: Path):
        """import_run raises StorageError on invalid ZIP file."""
        # Create invalid ZIP file
        bad_zip = tmp_path / "bad.zip"
        bad_zip.write_text("not a zip file")

        archiver = RunArchiver(base_dir=str(tmp_path))

        with pytest.raises(StorageError, match="Invalid ZIP file"):
            await archiver.import_run(str(bad_zip))

    @pytest.mark.asyncio
    async def test_import_run_raises_storage_error_on_invalid_structure(self, tmp_path: Path):
        """import_run raises StorageError if ZIP doesn't contain run directory."""
        zip_path = tmp_path / "invalid.zip"
        with zipfile.ZipFile(zip_path, "w") as zipf:
            # Wrong structure
            zipf.writestr("some/random/file.txt", "data")

        archiver = RunArchiver(base_dir=str(tmp_path))

        with pytest.raises(StorageError, match="No run directory found in ZIP"):
            await archiver.import_run(str(zip_path))

    @pytest.mark.asyncio
    async def test_export_import_round_trip(self, tmp_path: Path):
        """Export and import can be performed sequentially."""
        # Create original run
        run_dir = tmp_path / "evaluations" / "test" / "runs" / "run-roundtrip"
        run_dir.mkdir(parents=True)
        manifest_data = {"run_id": "run-roundtrip", "test": "data"}
        (run_dir / "manifest.json").write_text(json.dumps(manifest_data))
        (run_dir / "results.jsonl").write_text('{"result": 1}\n')

        # Export
        archiver1 = RunArchiver(base_dir=str(tmp_path))
        zip_path = str(tmp_path / "roundtrip.zip")
        await archiver1.export_run(run_id="run-roundtrip", output_path=zip_path)

        # Verify ZIP was created
        assert Path(zip_path).exists()

        # Verify ZIP contains expected structure
        with zipfile.ZipFile(zip_path, "r") as zipf:
            names = zipf.namelist()
            assert any("manifest.json" in name for name in names)
