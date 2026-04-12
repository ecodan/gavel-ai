import pytest

pytestmark = pytest.mark.unit
"""
Unit tests for ReportRunnerStep.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gavel_ai.core.exceptions import ConfigError
from gavel_ai.core.steps.base import StepPhase
from gavel_ai.core.steps.report_runner import ReportRunnerStep, RunData
from gavel_ai.models import EvalConfig
from gavel_ai.models.config import TestSubject
from gavel_ai.models.runtime import OutputRecord


class TestRunData:
    """Test RunData dataclass."""

    def test_run_data_init_defaults(self):
        """RunData initializes with empty defaults."""
        data = RunData()

        assert data.metadata == {}
        assert data.results == []
        assert data.telemetry == {}

    def test_run_data_init_with_values(self):
        """RunData initializes with provided values."""
        data = RunData(
            metadata={"eval_name": "test"},
            results=[{"score": 8}],
            telemetry={"duration": 120},
        )

        assert data.metadata["eval_name"] == "test"
        assert len(data.results) == 1
        assert data.telemetry["duration"] == 120


def _make_output_record(scenario_id: str, variant_id: str, output: str = "output") -> OutputRecord:
    """Helper to create an OutputRecord for tests."""
    return OutputRecord(
        test_subject="test-subject",
        variant_id=variant_id,
        scenario_id=scenario_id,
        processor_output=output,
        timing_ms=0,
        tokens_prompt=0,
        tokens_completion=0,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _make_mock_context(
    tmp_path: Path,
    processor_results=None,
    evaluation_results=None,
    test_subjects=None,
    variants=None,
):
    """Build a standard mock context for ReportRunnerStep tests."""
    mock_eval_config = MagicMock(spec=EvalConfig)
    mock_eval_config.test_subject_type = "local"
    mock_eval_config.test_subjects = test_subjects or []
    mock_eval_config.variants = variants or ["v1"]

    mock_context = MagicMock()
    mock_context.eval_context.eval_config.read.return_value = mock_eval_config
    mock_context.eval_context.eval_name = "test-eval"
    mock_context.processor_results = processor_results or []
    mock_context.evaluation_results = evaluation_results or []
    mock_context.test_subject = "test-subject"
    mock_context.model_variant = "v1"
    mock_context.run_dir = tmp_path
    mock_context.run_id = "run-123"
    mock_context.results_judged = MagicMock()
    mock_context.results_raw = MagicMock()

    (tmp_path / ".config").mkdir(exist_ok=True)
    (tmp_path / ".config" / "agents.json").write_text("{}")
    (tmp_path / ".config" / "eval_config.json").write_text("{}")

    return mock_context


def _make_metadata_mock():
    """Build a standard mock metadata collector."""
    mock_metadata = MagicMock()
    mock_metadata.run_start_time = 1000.0
    mock_stats = MagicMock()
    mock_stats.total_duration_seconds = 120.0
    mock_stats.llm_calls.model_dump.return_value = {"count": 0}
    mock_stats.model_dump_json.return_value = '{"total_duration_seconds": 120.0}'
    mock_metadata.compute_statistics.return_value = mock_stats
    return mock_metadata


class TestReportRunnerStep:
    """Test ReportRunnerStep class."""

    def test_init(self, mock_logger: logging.Logger):
        """ReportRunnerStep initializes with logger."""
        step = ReportRunnerStep(mock_logger)

        assert step.logger == mock_logger

    def test_phase_property(self, mock_logger: logging.Logger):
        """phase property returns REPORTING."""
        step = ReportRunnerStep(mock_logger)

        assert step.phase == StepPhase.REPORTING

    @pytest.mark.asyncio
    async def test_execute_raises_config_error_if_no_processor_results(
        self, mock_logger: logging.Logger
    ):
        """execute raises ConfigError if processor_results is None."""
        step = ReportRunnerStep(mock_logger)

        mock_context = MagicMock()
        mock_context.processor_results = None

        with pytest.raises(ConfigError, match="requires processor_results"):
            await step.execute(mock_context)

    @pytest.mark.asyncio
    @patch("gavel_ai.core.steps.report_runner.compute_config_hash", return_value="hash123")
    @patch("gavel_ai.core.steps.report_runner.OneShotReporter")
    @patch("gavel_ai.core.steps.report_runner.get_metadata_collector")
    async def test_execute_does_not_touch_raw_results(
        self,
        mock_get_metadata,
        mock_reporter_class,
        mock_hash,
        mock_logger: logging.Logger,
        tmp_path: Path,
    ):
        """ReportRunnerStep must NOT call results_raw.append — raw results are streamed
        by ScenarioProcessorStep and must not be touched here."""
        step = ReportRunnerStep(mock_logger)

        record = _make_output_record("s1", "v1")
        mock_context = _make_mock_context(tmp_path, processor_results=[record])
        mock_get_metadata.return_value = _make_metadata_mock()

        mock_reporter = MagicMock()
        mock_reporter.generate = AsyncMock(return_value="<html></html>")
        mock_reporter_class.return_value = mock_reporter

        await step.execute(mock_context)

        mock_context.results_raw.append.assert_not_called()

    @pytest.mark.asyncio
    @patch("gavel_ai.core.steps.report_runner.compute_config_hash", return_value="hash123")
    @patch("gavel_ai.core.steps.report_runner.OneShotReporter")
    @patch("gavel_ai.core.steps.report_runner.get_metadata_collector")
    async def test_execute_writes_judged_entries_via_results_judged(
        self,
        mock_get_metadata,
        mock_reporter_class,
        mock_hash,
        mock_logger: logging.Logger,
        tmp_path: Path,
    ):
        """execute appends judged entries to results_judged using OutputRecord data."""
        step = ReportRunnerStep(mock_logger)

        record = _make_output_record("s1", "v1", output="my output")
        evaluation = {
            "scenario_id": "s1",
            "variant_id": "v1",
            "judges": [{"name": "judge1", "score": 8}],
        }
        mock_context = _make_mock_context(
            tmp_path, processor_results=[record], evaluation_results=[evaluation]
        )
        mock_get_metadata.return_value = _make_metadata_mock()

        mock_reporter = MagicMock()
        mock_reporter.generate = AsyncMock(return_value="<html></html>")
        mock_reporter_class.return_value = mock_reporter

        await step.execute(mock_context)

        mock_context.results_judged.append.assert_called_once()
        written_entry = mock_context.results_judged.append.call_args[0][0]
        assert written_entry["scenario_id"] == "s1"
        assert written_entry["variant_id"] == "v1"
        assert written_entry["processor_output"] == "my output"
        assert written_entry["judges"] == [{"name": "judge1", "score": 8}]
        assert "metadata" not in written_entry

    @pytest.mark.asyncio
    @patch("gavel_ai.core.steps.report_runner.compute_config_hash", return_value="hash123")
    @patch("gavel_ai.core.steps.report_runner.OneShotReporter")
    @patch("gavel_ai.core.steps.report_runner.get_metadata_collector")
    async def test_execute_joins_on_scenario_id_and_variant_id(
        self,
        mock_get_metadata,
        mock_reporter_class,
        mock_hash,
        mock_logger: logging.Logger,
        tmp_path: Path,
    ):
        """execute joins OutputRecord with evaluation on (scenario_id, variant_id),
        not by position — a record that has no matching evaluation gets empty judges."""
        step = ReportRunnerStep(mock_logger)

        # 2 variants × 2 scenarios = 4 records, but evaluations only cover v1
        records = [
            _make_output_record("s1", "v1"),
            _make_output_record("s2", "v1"),
            _make_output_record("s1", "v2"),
            _make_output_record("s2", "v2"),
        ]
        evaluations = [
            {"scenario_id": "s2", "variant_id": "v1", "judges": [{"score": 9}]},
            {"scenario_id": "s1", "variant_id": "v1", "judges": [{"score": 7}]},
        ]
        mock_context = _make_mock_context(
            tmp_path,
            processor_results=records,
            evaluation_results=evaluations,
            variants=["v1", "v2"],
        )
        mock_get_metadata.return_value = _make_metadata_mock()

        mock_reporter = MagicMock()
        mock_reporter.generate = AsyncMock(return_value="<html></html>")
        mock_reporter_class.return_value = mock_reporter

        await step.execute(mock_context)

        assert mock_context.results_judged.append.call_count == 4
        written = [call[0][0] for call in mock_context.results_judged.append.call_args_list]

        # Build a quick lookup for assertions
        by_key = {(e["scenario_id"], e["variant_id"]): e for e in written}

        assert by_key[("s1", "v1")]["judges"] == [{"score": 7}]
        assert by_key[("s2", "v1")]["judges"] == [{"score": 9}]
        assert by_key[("s1", "v2")]["judges"] == []  # No evaluation for v2
        assert by_key[("s2", "v2")]["judges"] == []  # No evaluation for v2

    @pytest.mark.asyncio
    @patch("gavel_ai.core.steps.report_runner.compute_config_hash", return_value="hash123")
    @patch("gavel_ai.core.steps.report_runner.OneShotReporter")
    @patch("gavel_ai.core.steps.report_runner.get_metadata_collector")
    async def test_execute_creates_manifest_json(
        self,
        mock_get_metadata,
        mock_reporter_class,
        mock_hash,
        mock_logger: logging.Logger,
        tmp_path: Path,
    ):
        """execute creates manifest.json with correct schema."""
        step = ReportRunnerStep(mock_logger)

        mock_judge = MagicMock()
        mock_judge.name = "judge1"
        mock_subject = MagicMock(spec=TestSubject)
        mock_subject.judges = [mock_judge]

        record = _make_output_record("s1", "v1")
        mock_context = _make_mock_context(
            tmp_path,
            processor_results=[record],
            test_subjects=[mock_subject],
        )
        mock_get_metadata.return_value = _make_metadata_mock()

        mock_reporter = MagicMock()
        mock_reporter.generate = AsyncMock(return_value="<html></html>")
        mock_reporter_class.return_value = mock_reporter

        await step.execute(mock_context)

        manifest_file = tmp_path / "manifest.json"
        assert manifest_file.exists()

        with open(manifest_file) as f:
            manifest = json.load(f)

        assert manifest["run_id"] == "run-123"
        assert manifest["eval_name"] == "test-eval"
        assert manifest["config_hash"] == "hash123"
        assert manifest["scenario_count"] == 1
        assert manifest["judge_count"] == 1
        assert manifest["status"] == "completed"

    @pytest.mark.asyncio
    @patch("gavel_ai.core.steps.report_runner.compute_config_hash", return_value="hash123")
    @patch("gavel_ai.core.steps.report_runner.OneShotReporter")
    @patch("gavel_ai.core.steps.report_runner.get_metadata_collector")
    async def test_execute_generates_report_html(
        self,
        mock_get_metadata,
        mock_reporter_class,
        mock_hash,
        mock_logger: logging.Logger,
        tmp_path: Path,
    ):
        """execute generates report.html via OneShotReporter."""
        step = ReportRunnerStep(mock_logger)

        mock_context = _make_mock_context(tmp_path)
        mock_get_metadata.return_value = _make_metadata_mock()

        mock_reporter = MagicMock()
        mock_reporter.generate = AsyncMock(return_value="<html>Test Report</html>")
        mock_reporter_class.return_value = mock_reporter

        await step.execute(mock_context)

        report_file = tmp_path / "report.html"
        assert report_file.exists()
        assert "Test Report" in report_file.read_text()
