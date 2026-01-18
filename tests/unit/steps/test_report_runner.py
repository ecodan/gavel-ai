"""
Unit tests for ReportRunnerStep.
"""

import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gavel_ai.core.exceptions import ConfigError
from gavel_ai.core.steps.base import StepPhase
from gavel_ai.core.steps.report_runner import ReportRunnerStep, RunData
from gavel_ai.models import EvalConfig
from gavel_ai.models.config import TestSubject
from gavel_ai.models.runtime import ProcessorResult


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
    @patch("gavel_ai.core.steps.report_runner.ResultsExporter")
    @patch("gavel_ai.core.steps.report_runner.OneShotReporter")
    @patch("gavel_ai.core.steps.report_runner.get_metadata_collector")
    async def test_execute_exports_raw_results(
        self,
        mock_get_metadata,
        mock_reporter_class,
        mock_exporter_class,
        mock_logger: logging.Logger,
        tmp_path: Path,
    ):
        """execute exports raw results via ResultsExporter."""
        step = ReportRunnerStep(mock_logger)

        mock_eval_config = MagicMock(spec=EvalConfig)
        mock_eval_config.test_subject_type = "local"
        mock_eval_config.test_subjects = []

        mock_scenario = MagicMock()
        mock_scenario.id = "s1"

        mock_processor_result = ProcessorResult(output="output", metadata={})

        mock_context = MagicMock()
        mock_context.eval_context.eval_config.read.return_value = mock_eval_config
        mock_context.eval_context.eval_name = "test-eval"
        mock_context.eval_context.scenarios.read.return_value = [mock_scenario]
        mock_context.processor_results = [mock_processor_result]
        mock_context.evaluation_results = []
        mock_context.test_subject = "test-subject"
        mock_context.model_variant = "test-variant"
        mock_context.run_dir = tmp_path
        mock_context.run_id = "run-123"

        # Mock metadata collector
        mock_metadata = MagicMock()
        mock_metadata.run_start_time = 1000.0
        mock_stats = MagicMock()
        mock_stats.total_duration_seconds = 120.0
        mock_stats.llm_calls.model_dump.return_value = {"count": 10}
        mock_stats.model_dump_json.return_value = '{"total_duration_seconds": 120.0}'
        mock_metadata.compute_statistics.return_value = mock_stats
        mock_get_metadata.return_value = mock_metadata

        # Mock exporter
        mock_exporter = MagicMock()
        mock_exporter.export_raw_results.return_value = tmp_path / "results_raw.jsonl"
        mock_exporter.export_judged_results.return_value = tmp_path / "results_judged.jsonl"
        mock_exporter.compute_config_hash.return_value = "hash123"
        mock_exporter_class.return_value = mock_exporter

        # Mock reporter
        mock_reporter = MagicMock()
        mock_reporter.generate = AsyncMock(return_value="<html>Report</html>")
        mock_reporter_class.return_value = mock_reporter

        # Create required directories
        (tmp_path / ".config").mkdir()
        (tmp_path / ".config" / "agents.json").write_text("{}")
        (tmp_path / ".config" / "eval_config.json").write_text("{}")

        await step.execute(mock_context)

        mock_exporter.export_raw_results.assert_called_once_with(
            [mock_scenario],
            [mock_processor_result],
            test_subject="test-subject",
            variant_id="test-variant",
        )

    @pytest.mark.asyncio
    @patch("gavel_ai.core.steps.report_runner.ResultsExporter")
    @patch("gavel_ai.core.steps.report_runner.OneShotReporter")
    @patch("gavel_ai.core.steps.report_runner.get_metadata_collector")
    async def test_execute_exports_judged_results(
        self,
        mock_get_metadata,
        mock_reporter_class,
        mock_exporter_class,
        mock_logger: logging.Logger,
        tmp_path: Path,
    ):
        """execute exports judged results via ResultsExporter."""
        step = ReportRunnerStep(mock_logger)

        mock_eval_config = MagicMock(spec=EvalConfig)
        mock_eval_config.test_subject_type = "local"
        mock_eval_config.test_subjects = []

        mock_scenario = MagicMock()
        mock_processor_result = ProcessorResult(output="output", metadata={})

        mock_evaluation = {"judges": [{"name": "judge1", "score": 8}]}

        mock_context = MagicMock()
        mock_context.eval_context.eval_config.read.return_value = mock_eval_config
        mock_context.eval_context.eval_name = "test-eval"
        mock_context.eval_context.scenarios.read.return_value = [mock_scenario]
        mock_context.processor_results = [mock_processor_result]
        mock_context.evaluation_results = [mock_evaluation]
        mock_context.test_subject = "test-subject"
        mock_context.model_variant = "test-variant"
        mock_context.run_dir = tmp_path
        mock_context.run_id = "run-123"

        mock_metadata = MagicMock()
        mock_metadata.run_start_time = 1000.0
        mock_stats = MagicMock()
        mock_stats.total_duration_seconds = 120.0
        mock_stats.llm_calls.model_dump.return_value = {}
        mock_stats.model_dump_json.return_value = '{"total_duration_seconds": 120.0}'
        mock_metadata.compute_statistics.return_value = mock_stats
        mock_get_metadata.return_value = mock_metadata

        mock_exporter = MagicMock()
        mock_exporter.export_raw_results.return_value = tmp_path / "results_raw.jsonl"
        mock_exporter.export_judged_results.return_value = tmp_path / "results_judged.jsonl"
        mock_exporter.compute_config_hash.return_value = "hash123"
        mock_exporter_class.return_value = mock_exporter

        mock_reporter = MagicMock()
        mock_reporter.generate = AsyncMock(return_value="<html></html>")
        mock_reporter_class.return_value = mock_reporter

        (tmp_path / ".config").mkdir()
        (tmp_path / ".config" / "agents.json").write_text("{}")
        (tmp_path / ".config" / "eval_config.json").write_text("{}")

        await step.execute(mock_context)

        mock_exporter.export_judged_results.assert_called_once_with(
            scenarios=[mock_scenario],
            processor_results=[mock_processor_result],
            judge_evaluations=[mock_evaluation],
            test_subject="test-subject",
            variant_id="test-variant",
        )

    @pytest.mark.asyncio
    @patch("gavel_ai.core.steps.report_runner.ResultsExporter")
    @patch("gavel_ai.core.steps.report_runner.OneShotReporter")
    @patch("gavel_ai.core.steps.report_runner.get_metadata_collector")
    async def test_execute_creates_manifest_json(
        self,
        mock_get_metadata,
        mock_reporter_class,
        mock_exporter_class,
        mock_logger: logging.Logger,
        tmp_path: Path,
    ):
        """execute creates manifest.json with correct schema."""
        step = ReportRunnerStep(mock_logger)

        mock_eval_config = MagicMock(spec=EvalConfig)
        mock_eval_config.test_subject_type = "local"
        mock_judge = MagicMock()
        mock_judge.name = "judge1"
        mock_subject = MagicMock(spec=TestSubject)
        mock_subject.judges = [mock_judge]
        mock_eval_config.test_subjects = [mock_subject]

        mock_scenario = MagicMock()

        mock_context = MagicMock()
        mock_context.eval_context.eval_config.read.return_value = mock_eval_config
        mock_context.eval_context.eval_name = "test-eval"
        mock_context.eval_context.scenarios.read.return_value = [mock_scenario]
        mock_context.processor_results = [ProcessorResult(output="out", metadata={})]
        mock_context.evaluation_results = []
        mock_context.test_subject = "test"
        mock_context.model_variant = "variant"
        mock_context.run_dir = tmp_path
        mock_context.run_id = "run-123"

        mock_metadata = MagicMock()
        mock_metadata.run_start_time = 1000.0
        mock_stats = MagicMock()
        mock_stats.total_duration_seconds = 120.0
        mock_stats.llm_calls.model_dump.return_value = {}
        mock_stats.model_dump_json.return_value = '{"total_duration_seconds": 120.0}'
        mock_metadata.compute_statistics.return_value = mock_stats
        mock_get_metadata.return_value = mock_metadata

        mock_exporter = MagicMock()
        mock_exporter.export_raw_results.return_value = tmp_path / "results_raw.jsonl"
        mock_exporter.export_judged_results.return_value = tmp_path / "results_judged.jsonl"
        mock_exporter.compute_config_hash.return_value = "hash123"
        mock_exporter_class.return_value = mock_exporter

        mock_reporter = MagicMock()
        mock_reporter.generate = AsyncMock(return_value="<html></html>")
        mock_reporter_class.return_value = mock_reporter

        (tmp_path / ".config").mkdir()
        (tmp_path / ".config" / "agents.json").write_text("{}")
        (tmp_path / ".config" / "eval_config.json").write_text("{}")

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
    @patch("gavel_ai.core.steps.report_runner.ResultsExporter")
    @patch("gavel_ai.core.steps.report_runner.OneShotReporter")
    @patch("gavel_ai.core.steps.report_runner.get_metadata_collector")
    async def test_execute_generates_report_html(
        self,
        mock_get_metadata,
        mock_reporter_class,
        mock_exporter_class,
        mock_logger: logging.Logger,
        tmp_path: Path,
    ):
        """execute generates report.html via OneShotReporter."""
        step = ReportRunnerStep(mock_logger)

        mock_eval_config = MagicMock(spec=EvalConfig)
        mock_eval_config.test_subject_type = "local"
        mock_eval_config.test_subjects = []

        mock_context = MagicMock()
        mock_context.eval_context.eval_config.read.return_value = mock_eval_config
        mock_context.eval_context.eval_name = "test-eval"
        mock_context.eval_context.scenarios.read.return_value = []
        mock_context.processor_results = []
        mock_context.evaluation_results = []
        mock_context.test_subject = "test"
        mock_context.model_variant = "variant"
        mock_context.run_dir = tmp_path
        mock_context.run_id = "run-123"

        mock_metadata = MagicMock()
        mock_metadata.run_start_time = 1000.0
        mock_stats = MagicMock()
        mock_stats.total_duration_seconds = 120.0
        mock_stats.llm_calls.model_dump.return_value = {"count": 5}
        mock_stats.model_dump_json.return_value = '{"total_duration_seconds": 120.0}'
        mock_metadata.compute_statistics.return_value = mock_stats
        mock_get_metadata.return_value = mock_metadata

        mock_exporter = MagicMock()
        mock_exporter.export_raw_results.return_value = tmp_path / "results_raw.jsonl"
        mock_exporter.export_judged_results.return_value = tmp_path / "results_judged.jsonl"
        mock_exporter.compute_config_hash.return_value = "hash123"
        mock_exporter_class.return_value = mock_exporter

        mock_reporter = MagicMock()
        mock_reporter.generate = AsyncMock(return_value="<html>Test Report</html>")
        mock_reporter_class.return_value = mock_reporter

        (tmp_path / ".config").mkdir()
        (tmp_path / ".config" / "agents.json").write_text("{}")
        (tmp_path / ".config" / "eval_config.json").write_text("{}")

        await step.execute(mock_context)

        report_file = tmp_path / "report.html"
        assert report_file.exists()

        report_content = report_file.read_text()
        assert "Test Report" in report_content
