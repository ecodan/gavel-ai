"""
Unit tests for RunContext SDK wrapper.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gavel_ai.core.exceptions import StorageError
from gavel_ai.models.runtime import Manifest
from gavel_ai.storage.context import RunContext


class TestRunContext:
    """Test RunContext class."""

    def test_init(self):
        """RunContext initializes with LocalFilesystemRun."""
        mock_run = MagicMock()
        mock_run.run_id = "run-123"
        mock_run.eval_name = "test-eval"

        ctx = RunContext(mock_run)

        assert ctx.run is mock_run

    @pytest.mark.asyncio
    @patch("gavel_ai.storage.context.LocalFilesystemRun")
    async def test_load_creates_run_context(self, mock_run_class):
        """load() creates RunContext from run_id."""
        mock_run = MagicMock()
        mock_run.run_id = "run-123"
        mock_run_class.load = AsyncMock(return_value=mock_run)

        ctx = await RunContext.load("run-123")

        mock_run_class.load.assert_called_once_with("run-123", ".gavel")
        assert ctx.run == mock_run

    @pytest.mark.asyncio
    @patch("gavel_ai.storage.context.LocalFilesystemRun")
    async def test_load_with_custom_base_dir(self, mock_run_class):
        """load() accepts custom base_dir."""
        mock_run = MagicMock()
        mock_run_class.load = AsyncMock(return_value=mock_run)

        await RunContext.load("run-123", base_dir="/custom/path")

        mock_run_class.load.assert_called_once_with("run-123", "/custom/path")

    def test_get_manifest_returns_manifest_model(self):
        """get_manifest() returns Manifest model."""
        from datetime import datetime

        mock_run = MagicMock()
        mock_run.manifest_data = {
            "timestamp": datetime.fromisoformat("2025-01-01T00:00:00"),
            "config_hash": "abc123",
            "scenario_count": 10,
            "variant_count": 1,
            "judge_versions": [{"judge1": "v1"}, {"judge2": "v2"}],
            "status": "completed",
            "duration": 120.5,
        }

        ctx = RunContext(mock_run)
        manifest = ctx.get_manifest()

        assert isinstance(manifest, Manifest)
        assert manifest.scenario_count == 10
        assert manifest.status == "completed"

    def test_get_manifest_raises_storage_error_if_not_loaded(self):
        """get_manifest() raises StorageError if manifest not loaded."""
        mock_run = MagicMock()
        mock_run.manifest_data = None

        ctx = RunContext(mock_run)

        with pytest.raises(StorageError, match="Manifest not loaded"):
            ctx.get_manifest()

    def test_get_results_returns_results_list(self):
        """get_results() returns list of result dicts."""
        mock_run = MagicMock()
        mock_run.results_data = [
            {"scenario_id": "s1", "score": 8},
            {"scenario_id": "s2", "score": 9},
        ]

        ctx = RunContext(mock_run)
        results = ctx.get_results()

        assert len(results) == 2
        assert results[0]["scenario_id"] == "s1"
        assert results[1]["score"] == 9

    def test_get_results_returns_empty_list_if_none(self):
        """get_results() returns empty list if no results."""
        mock_run = MagicMock()
        mock_run.results_data = None

        ctx = RunContext(mock_run)
        results = ctx.get_results()

        assert results == []

    def test_get_telemetry_returns_telemetry_list(self):
        """get_telemetry() returns list of telemetry events."""
        mock_run = MagicMock()
        mock_run.telemetry_data = [
            {"event": "start", "timestamp": "2025-01-01T00:00:00"},
            {"event": "end", "timestamp": "2025-01-01T00:05:00"},
        ]

        ctx = RunContext(mock_run)
        telemetry = ctx.get_telemetry()

        assert len(telemetry) == 2
        assert telemetry[0]["event"] == "start"
        assert telemetry[1]["event"] == "end"

    def test_get_telemetry_returns_empty_list_if_none(self):
        """get_telemetry() returns empty list if no telemetry."""
        mock_run = MagicMock()
        mock_run.telemetry_data = None

        ctx = RunContext(mock_run)
        telemetry = ctx.get_telemetry()

        assert telemetry == []

    def test_get_config_returns_config_dict(self):
        """get_config() returns configuration dict."""
        mock_run = MagicMock()
        mock_run.config_data = {
            "eval_config": {"name": "test"},
            "agents": {"agent1": {"model": "claude"}},
        }

        ctx = RunContext(mock_run)
        config = ctx.get_config()

        assert config["eval_config"]["name"] == "test"
        assert "agents" in config

    def test_get_config_returns_empty_dict_if_none(self):
        """get_config() returns empty dict if no config."""
        mock_run = MagicMock()
        mock_run.config_data = None

        ctx = RunContext(mock_run)
        config = ctx.get_config()

        assert config == {}

    def test_get_metadata_returns_metadata_dict(self):
        """get_metadata() returns metadata dict."""
        mock_run = MagicMock()
        mock_run.metadata_data = {
            "duration": 120,
            "llm_calls": 50,
        }

        ctx = RunContext(mock_run)
        metadata = ctx.get_metadata()

        assert metadata["duration"] == 120
        assert metadata["llm_calls"] == 50

    def test_get_metadata_returns_empty_dict_if_none(self):
        """get_metadata() returns empty dict if no metadata."""
        mock_run = MagicMock()
        mock_run.metadata_data = None

        ctx = RunContext(mock_run)
        metadata = ctx.get_metadata()

        assert metadata == {}

    def test_get_log_returns_log_string(self):
        """get_log() returns log content as string."""
        mock_run = MagicMock()
        mock_run.log_data = "2025-01-01 00:00:00 [INFO] Test started\n2025-01-01 00:05:00 [INFO] Test completed\n"

        ctx = RunContext(mock_run)
        log = ctx.get_log()

        assert "Test started" in log
        assert "Test completed" in log

    def test_get_log_returns_empty_string_if_none(self):
        """get_log() returns empty string if no log."""
        mock_run = MagicMock()
        mock_run.log_data = None

        ctx = RunContext(mock_run)
        log = ctx.get_log()

        assert log == ""

    def test_get_report_returns_report_html(self):
        """get_report() returns report HTML content."""
        mock_run = MagicMock()
        mock_run.report_data = "<html><body>Test Report</body></html>"

        ctx = RunContext(mock_run)
        report = ctx.get_report()

        assert "<html>" in report
        assert "Test Report" in report

    def test_get_report_returns_empty_string_if_none(self):
        """get_report() returns empty string if no report."""
        mock_run = MagicMock()
        mock_run.report_data = None

        ctx = RunContext(mock_run)
        report = ctx.get_report()

        assert report == ""

    def test_run_id_property(self):
        """run_id property returns run ID."""
        mock_run = MagicMock()
        mock_run.run_id = "run-123"

        ctx = RunContext(mock_run)

        assert ctx.run_id == "run-123"

    def test_eval_name_property(self):
        """eval_name property returns evaluation name."""
        mock_run = MagicMock()
        mock_run.eval_name = "test-eval"

        ctx = RunContext(mock_run)

        assert ctx.eval_name == "test-eval"

    def test_run_dir_property(self):
        """run_dir property returns run directory path."""
        mock_run = MagicMock()
        mock_run.run_dir = Path("/path/to/runs/run-123")

        ctx = RunContext(mock_run)

        assert ctx.run_dir == Path("/path/to/runs/run-123")

    @pytest.mark.asyncio
    async def test_usage_example_in_notebook(self):
        """RunContext provides SDK-style access for notebooks."""
        from datetime import datetime

        # Simulate notebook usage
        mock_run = MagicMock()
        mock_run.run_id = "run-notebook"
        mock_run.eval_name = "notebook-eval"
        mock_run.results_data = [{"scenario_id": "s1", "score": 8}]
        mock_run.manifest_data = {
            "timestamp": datetime.fromisoformat("2025-01-01T00:00:00"),
            "config_hash": "abc",
            "scenario_count": 1,
            "variant_count": 1,
            "judge_versions": [{"judge1": "v1"}],
            "status": "completed",
            "duration": 60.0,
        }

        ctx = RunContext(mock_run)

        # Verify SDK-style access works
        results = ctx.get_results()
        assert len(results) == 1

        manifest = ctx.get_manifest()
        assert manifest.status == "completed"

        assert ctx.run_id == "run-notebook"
        assert ctx.eval_name == "notebook-eval"
