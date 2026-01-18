"""
Unit tests for RunCleaner.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from gavel_ai.storage.cleanup import RunCleaner


class TestRunCleaner:
    """Test RunCleaner class."""

    def test_init_default_base_dir(self):
        """RunCleaner initializes with default base_dir."""
        cleaner = RunCleaner()
        assert cleaner.base_dir == Path(".gavel")

    def test_init_custom_base_dir(self):
        """RunCleaner initializes with custom base_dir."""
        cleaner = RunCleaner(base_dir="/custom/path")
        assert cleaner.base_dir == Path("/custom/path")

    def test_parse_time_expression_days(self):
        """parse_time_expression parses days correctly."""
        cleaner = RunCleaner()
        assert cleaner.parse_time_expression("30d") == 30
        assert cleaner.parse_time_expression("1d") == 1
        assert cleaner.parse_time_expression("365d") == 365

    def test_parse_time_expression_weeks(self):
        """parse_time_expression parses weeks correctly."""
        cleaner = RunCleaner()
        assert cleaner.parse_time_expression("1w") == 7
        assert cleaner.parse_time_expression("2w") == 14
        assert cleaner.parse_time_expression("4w") == 28

    def test_parse_time_expression_months(self):
        """parse_time_expression parses months correctly."""
        cleaner = RunCleaner()
        assert cleaner.parse_time_expression("1m") == 30
        assert cleaner.parse_time_expression("2m") == 60
        assert cleaner.parse_time_expression("12m") == 360

    def test_parse_time_expression_years(self):
        """parse_time_expression parses years correctly."""
        cleaner = RunCleaner()
        assert cleaner.parse_time_expression("1y") == 365
        assert cleaner.parse_time_expression("2y") == 730

    def test_parse_time_expression_case_insensitive(self):
        """parse_time_expression is case insensitive."""
        cleaner = RunCleaner()
        assert cleaner.parse_time_expression("30D") == 30
        assert cleaner.parse_time_expression("1W") == 7
        assert cleaner.parse_time_expression("2M") == 60
        assert cleaner.parse_time_expression("1Y") == 365

    def test_parse_time_expression_invalid_format_raises_value_error(self):
        """parse_time_expression raises ValueError on invalid format."""
        cleaner = RunCleaner()

        with pytest.raises(ValueError, match="Invalid time expression"):
            cleaner.parse_time_expression("30")

        with pytest.raises(ValueError, match="Invalid time expression"):
            cleaner.parse_time_expression("days")

        with pytest.raises(ValueError, match="Invalid time expression"):
            cleaner.parse_time_expression("30x")

        with pytest.raises(ValueError, match="Invalid time expression"):
            cleaner.parse_time_expression("abc")

    @pytest.mark.asyncio
    async def test_cleanup_runs_dry_run_default(self, tmp_path: Path):
        """cleanup_runs defaults to dry_run=True."""
        # Create old run
        run_dir = tmp_path / "evaluations" / "test" / "runs" / "run-old"
        run_dir.mkdir(parents=True)

        old_timestamp = (datetime.now() - timedelta(days=60)).isoformat()
        manifest = {"timestamp": old_timestamp, "is_milestone": False}
        (run_dir / "manifest.json").write_text(json.dumps(manifest))

        cleaner = RunCleaner(base_dir=str(tmp_path))

        # Dry run - should return runs but not delete
        deleted = await cleaner.cleanup_runs(older_than=30)

        assert "run-old" in deleted
        assert run_dir.exists()  # Still exists in dry run

    @pytest.mark.asyncio
    async def test_cleanup_runs_deletes_old_runs(self, tmp_path: Path):
        """cleanup_runs deletes runs older than threshold."""
        # Create old run
        run_dir = tmp_path / "evaluations" / "test" / "runs" / "run-old"
        run_dir.mkdir(parents=True)

        old_timestamp = (datetime.now() - timedelta(days=60)).isoformat()
        manifest = {"timestamp": old_timestamp, "is_milestone": False}
        (run_dir / "manifest.json").write_text(json.dumps(manifest))

        cleaner = RunCleaner(base_dir=str(tmp_path))

        deleted = await cleaner.cleanup_runs(older_than=30, dry_run=False)

        assert "run-old" in deleted
        assert not run_dir.exists()  # Deleted

    @pytest.mark.asyncio
    async def test_cleanup_runs_preserves_milestone_runs(self, tmp_path: Path):
        """cleanup_runs preserves milestone runs regardless of age."""
        # Create old milestone run
        run_dir = tmp_path / "evaluations" / "test" / "runs" / "run-milestone"
        run_dir.mkdir(parents=True)

        old_timestamp = (datetime.now() - timedelta(days=365)).isoformat()
        manifest = {"timestamp": old_timestamp, "is_milestone": True}
        (run_dir / "manifest.json").write_text(json.dumps(manifest))

        cleaner = RunCleaner(base_dir=str(tmp_path))

        deleted = await cleaner.cleanup_runs(older_than=30, dry_run=False)

        assert "run-milestone" not in deleted
        assert run_dir.exists()  # Preserved

    @pytest.mark.asyncio
    async def test_cleanup_runs_preserves_recent_runs(self, tmp_path: Path):
        """cleanup_runs preserves runs newer than threshold."""
        # Create recent run
        run_dir = tmp_path / "evaluations" / "test" / "runs" / "run-recent"
        run_dir.mkdir(parents=True)

        recent_timestamp = (datetime.now() - timedelta(days=5)).isoformat()
        manifest = {"timestamp": recent_timestamp, "is_milestone": False}
        (run_dir / "manifest.json").write_text(json.dumps(manifest))

        cleaner = RunCleaner(base_dir=str(tmp_path))

        deleted = await cleaner.cleanup_runs(older_than=30, dry_run=False)

        assert "run-recent" not in deleted
        assert run_dir.exists()  # Preserved

    @pytest.mark.asyncio
    async def test_cleanup_runs_accepts_string_time_expression(self, tmp_path: Path):
        """cleanup_runs accepts string time expressions."""
        run_dir = tmp_path / "evaluations" / "test" / "runs" / "run-old"
        run_dir.mkdir(parents=True)

        old_timestamp = (datetime.now() - timedelta(days=60)).isoformat()
        manifest = {"timestamp": old_timestamp, "is_milestone": False}
        (run_dir / "manifest.json").write_text(json.dumps(manifest))

        cleaner = RunCleaner(base_dir=str(tmp_path))

        deleted = await cleaner.cleanup_runs(older_than="1m", dry_run=False)

        assert "run-old" in deleted

    @pytest.mark.asyncio
    async def test_cleanup_runs_accepts_integer_days(self, tmp_path: Path):
        """cleanup_runs accepts integer days directly."""
        run_dir = tmp_path / "evaluations" / "test" / "runs" / "run-old"
        run_dir.mkdir(parents=True)

        old_timestamp = (datetime.now() - timedelta(days=60)).isoformat()
        manifest = {"timestamp": old_timestamp, "is_milestone": False}
        (run_dir / "manifest.json").write_text(json.dumps(manifest))

        cleaner = RunCleaner(base_dir=str(tmp_path))

        deleted = await cleaner.cleanup_runs(older_than=30, dry_run=False)

        assert "run-old" in deleted

    @pytest.mark.asyncio
    async def test_cleanup_runs_filters_by_eval_name(self, tmp_path: Path):
        """cleanup_runs filters by eval_name when specified."""
        # Create runs in different evaluations
        run1_dir = tmp_path / "evaluations" / "eval1" / "runs" / "run-1"
        run1_dir.mkdir(parents=True)
        run2_dir = tmp_path / "evaluations" / "eval2" / "runs" / "run-2"
        run2_dir.mkdir(parents=True)

        old_timestamp = (datetime.now() - timedelta(days=60)).isoformat()

        for run_dir, run_id in [(run1_dir, "run-1"), (run2_dir, "run-2")]:
            manifest = {"timestamp": old_timestamp, "is_milestone": False}
            (run_dir / "manifest.json").write_text(json.dumps(manifest))

        cleaner = RunCleaner(base_dir=str(tmp_path))

        # Clean only eval1
        deleted = await cleaner.cleanup_runs(older_than=30, eval_name="eval1", dry_run=False)

        assert "run-1" in deleted
        assert "run-2" not in deleted
        assert not run1_dir.exists()
        assert run2_dir.exists()

    @pytest.mark.asyncio
    async def test_cleanup_runs_skips_corrupted_manifests(self, tmp_path: Path):
        """cleanup_runs skips runs with corrupted manifests."""
        # Create run with corrupted manifest
        run_dir = tmp_path / "evaluations" / "test" / "runs" / "run-corrupted"
        run_dir.mkdir(parents=True)
        (run_dir / "manifest.json").write_text("{ invalid json }")

        # Create valid old run
        run2_dir = tmp_path / "evaluations" / "test" / "runs" / "run-old"
        run2_dir.mkdir(parents=True)
        old_timestamp = (datetime.now() - timedelta(days=60)).isoformat()
        manifest = {"timestamp": old_timestamp, "is_milestone": False}
        (run2_dir / "manifest.json").write_text(json.dumps(manifest))

        cleaner = RunCleaner(base_dir=str(tmp_path))

        deleted = await cleaner.cleanup_runs(older_than=30, dry_run=False)

        # Corrupted run should be skipped
        assert "run-corrupted" not in deleted
        assert run_dir.exists()

        # Valid old run should be deleted
        assert "run-old" in deleted
        assert not run2_dir.exists()

    @pytest.mark.asyncio
    async def test_cleanup_runs_skips_missing_timestamp(self, tmp_path: Path):
        """cleanup_runs skips runs without timestamp in manifest."""
        run_dir = tmp_path / "evaluations" / "test" / "runs" / "run-no-timestamp"
        run_dir.mkdir(parents=True)

        manifest = {"is_milestone": False}  # No timestamp
        (run_dir / "manifest.json").write_text(json.dumps(manifest))

        cleaner = RunCleaner(base_dir=str(tmp_path))

        deleted = await cleaner.cleanup_runs(older_than=30, dry_run=False)

        assert "run-no-timestamp" not in deleted
        assert run_dir.exists()

    @pytest.mark.asyncio
    async def test_cleanup_runs_returns_empty_list_if_no_runs(self, tmp_path: Path):
        """cleanup_runs returns empty list if no runs to delete."""
        cleaner = RunCleaner(base_dir=str(tmp_path))

        deleted = await cleaner.cleanup_runs(older_than=30, dry_run=False)

        assert deleted == []

    @pytest.mark.asyncio
    async def test_cleanup_runs_handles_multiple_runs(self, tmp_path: Path):
        """cleanup_runs handles multiple old runs correctly."""
        # Create 3 old runs
        for i in range(3):
            run_dir = tmp_path / "evaluations" / "test" / "runs" / f"run-{i}"
            run_dir.mkdir(parents=True)

            old_timestamp = (datetime.now() - timedelta(days=60)).isoformat()
            manifest = {"timestamp": old_timestamp, "is_milestone": False}
            (run_dir / "manifest.json").write_text(json.dumps(manifest))

        cleaner = RunCleaner(base_dir=str(tmp_path))

        deleted = await cleaner.cleanup_runs(older_than=30, dry_run=False)

        assert len(deleted) == 3
        assert "run-0" in deleted
        assert "run-1" in deleted
        assert "run-2" in deleted
