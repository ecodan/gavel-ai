import pytest

pytestmark = pytest.mark.unit
"""
Unit tests for OneShotWorkflow orchestrator.
"""

import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gavel_ai.core.workflows.oneshot import OneShotWorkflow, ProcessorError


class TestOneShotWorkflow:
    """Test OneShotWorkflow class."""

    def test_init(self, mock_logger: logging.Logger):
        """OneShotWorkflow initializes with eval_ctx and logger."""
        mock_eval_ctx = MagicMock()
        mock_eval_ctx.eval_name = "test_eval"

        workflow = OneShotWorkflow(mock_eval_ctx, mock_logger)

        assert workflow.eval_ctx == mock_eval_ctx
        assert workflow.logger == mock_logger

    @pytest.mark.asyncio
    @patch("gavel_ai.core.workflows.oneshot.configure_run_telemetry")
    @patch("gavel_ai.core.workflows.oneshot.get_metadata_collector")
    @patch("gavel_ai.core.workflows.oneshot.reset_telemetry")
    @patch("gavel_ai.core.workflows.oneshot.reset_metadata_collector")
    @patch("gavel_ai.core.workflows.oneshot.LocalRunContext")
    async def test_execute_creates_run_context(
        self,
        mock_run_context_class,
        mock_reset_metadata,
        mock_reset_telemetry,
        mock_get_metadata,
        mock_configure_telemetry,
        mock_logger: logging.Logger,
    ):
        """execute() creates LocalRunContext with correct parameters."""
        mock_eval_ctx = MagicMock()
        mock_eval_ctx.eval_name = "test_eval"
        mock_eval_ctx.eval_dir = Path(".gavel/evaluations/test_eval")

        mock_run_ctx = MagicMock()
        mock_run_ctx.run_id = "run-123"
        mock_run_ctx.run_logger = mock_logger
        mock_run_context_class.return_value = mock_run_ctx

        mock_metadata = MagicMock()
        mock_get_metadata.return_value = mock_metadata

        workflow = OneShotWorkflow(mock_eval_ctx, mock_logger)
        workflow._execute_steps = AsyncMock()

        await workflow.execute()

        mock_run_context_class.assert_called_once_with(
            eval_ctx=mock_eval_ctx, base_dir=Path(".gavel/evaluations/test_eval/runs")
        )

    @pytest.mark.asyncio
    @patch("gavel_ai.core.workflows.oneshot.configure_run_telemetry")
    @patch("gavel_ai.core.workflows.oneshot.get_metadata_collector")
    @patch("gavel_ai.core.workflows.oneshot.reset_telemetry")
    @patch("gavel_ai.core.workflows.oneshot.reset_metadata_collector")
    @patch("gavel_ai.core.workflows.oneshot.LocalRunContext")
    async def test_execute_configures_telemetry(
        self,
        mock_run_context_class,
        mock_reset_metadata,
        mock_reset_telemetry,
        mock_get_metadata,
        mock_configure_telemetry,
        mock_logger: logging.Logger,
    ):
        """execute() configures telemetry for the run."""
        mock_eval_ctx = MagicMock()
        mock_eval_ctx.eval_name = "test_eval"
        mock_eval_ctx.eval_root = Path(".gavel/evaluations")

        mock_run_ctx = MagicMock()
        mock_run_ctx.run_id = "run-123"
        mock_run_ctx.run_logger = mock_logger
        mock_run_context_class.return_value = mock_run_ctx

        mock_metadata = MagicMock()
        mock_get_metadata.return_value = mock_metadata

        workflow = OneShotWorkflow(mock_eval_ctx, mock_logger)
        workflow._execute_steps = AsyncMock()

        await workflow.execute()

        mock_configure_telemetry.assert_called_once_with(
            run_id="run-123", eval_name="test_eval", base_dir=".gavel"
        )

    @pytest.mark.asyncio
    @patch("gavel_ai.core.workflows.oneshot.configure_run_telemetry")
    @patch("gavel_ai.core.workflows.oneshot.get_metadata_collector")
    @patch("gavel_ai.core.workflows.oneshot.reset_telemetry")
    @patch("gavel_ai.core.workflows.oneshot.reset_metadata_collector")
    @patch("gavel_ai.core.workflows.oneshot.LocalRunContext")
    async def test_execute_records_run_start(
        self,
        mock_run_context_class,
        mock_reset_metadata,
        mock_reset_telemetry,
        mock_get_metadata,
        mock_configure_telemetry,
        mock_logger: logging.Logger,
    ):
        """execute() records run start via metadata collector."""
        mock_eval_ctx = MagicMock()
        mock_eval_ctx.eval_name = "test_eval"

        mock_run_ctx = MagicMock()
        mock_run_ctx.run_id = "run-123"
        mock_run_ctx.run_logger = mock_logger
        mock_run_context_class.return_value = mock_run_ctx

        mock_metadata = MagicMock()
        mock_get_metadata.return_value = mock_metadata

        workflow = OneShotWorkflow(mock_eval_ctx, mock_logger)
        workflow._execute_steps = AsyncMock()

        await workflow.execute()

        mock_metadata.record_run_start.assert_called_once()

    @pytest.mark.asyncio
    @patch("gavel_ai.core.workflows.oneshot.configure_run_telemetry")
    @patch("gavel_ai.core.workflows.oneshot.get_metadata_collector")
    @patch("gavel_ai.core.workflows.oneshot.reset_telemetry")
    @patch("gavel_ai.core.workflows.oneshot.reset_metadata_collector")
    @patch("gavel_ai.core.workflows.oneshot.LocalRunContext")
    async def test_execute_calls_execute_steps(
        self,
        mock_run_context_class,
        mock_reset_metadata,
        mock_reset_telemetry,
        mock_get_metadata,
        mock_configure_telemetry,
        mock_logger: logging.Logger,
    ):
        """execute() calls _execute_steps with run context."""
        mock_eval_ctx = MagicMock()
        mock_eval_ctx.eval_name = "test_eval"

        mock_run_ctx = MagicMock()
        mock_run_ctx.run_id = "run-123"
        mock_run_ctx.run_logger = mock_logger
        mock_run_context_class.return_value = mock_run_ctx

        mock_metadata = MagicMock()
        mock_get_metadata.return_value = mock_metadata

        workflow = OneShotWorkflow(mock_eval_ctx, mock_logger)
        workflow._execute_steps = AsyncMock()

        await workflow.execute()

        workflow._execute_steps.assert_called_once_with(mock_run_ctx)

    @pytest.mark.asyncio
    @patch("gavel_ai.core.workflows.oneshot.configure_run_telemetry")
    @patch("gavel_ai.core.workflows.oneshot.get_metadata_collector")
    @patch("gavel_ai.core.workflows.oneshot.reset_telemetry")
    @patch("gavel_ai.core.workflows.oneshot.reset_metadata_collector")
    @patch("gavel_ai.core.workflows.oneshot.LocalRunContext")
    async def test_execute_returns_run_context(
        self,
        mock_run_context_class,
        mock_reset_metadata,
        mock_reset_telemetry,
        mock_get_metadata,
        mock_configure_telemetry,
        mock_logger: logging.Logger,
    ):
        """execute() returns the created run context."""
        mock_eval_ctx = MagicMock()
        mock_eval_ctx.eval_name = "test_eval"

        mock_run_ctx = MagicMock()
        mock_run_ctx.run_id = "run-123"
        mock_run_ctx.run_logger = mock_logger
        mock_run_context_class.return_value = mock_run_ctx

        mock_metadata = MagicMock()
        mock_get_metadata.return_value = mock_metadata

        workflow = OneShotWorkflow(mock_eval_ctx, mock_logger)
        workflow._execute_steps = AsyncMock()

        result = await workflow.execute()

        assert result == mock_run_ctx

    @pytest.mark.asyncio
    @patch("gavel_ai.core.workflows.oneshot.configure_run_telemetry")
    @patch("gavel_ai.core.workflows.oneshot.get_metadata_collector")
    @patch("gavel_ai.core.workflows.oneshot.reset_telemetry")
    @patch("gavel_ai.core.workflows.oneshot.reset_metadata_collector")
    @patch("gavel_ai.core.workflows.oneshot.LocalRunContext")
    async def test_execute_resets_telemetry_on_success(
        self,
        mock_run_context_class,
        mock_reset_metadata,
        mock_reset_telemetry,
        mock_get_metadata,
        mock_configure_telemetry,
        mock_logger: logging.Logger,
    ):
        """execute() resets telemetry and metadata after successful execution."""
        mock_eval_ctx = MagicMock()
        mock_eval_ctx.eval_name = "test_eval"

        mock_run_ctx = MagicMock()
        mock_run_ctx.run_id = "run-123"
        mock_run_ctx.run_logger = mock_logger
        mock_run_context_class.return_value = mock_run_ctx

        mock_metadata = MagicMock()
        mock_get_metadata.return_value = mock_metadata

        workflow = OneShotWorkflow(mock_eval_ctx, mock_logger)
        workflow._execute_steps = AsyncMock()

        await workflow.execute()

        mock_reset_telemetry.assert_called_once()
        mock_reset_metadata.assert_called_once()

    @pytest.mark.asyncio
    @patch("gavel_ai.core.workflows.oneshot.configure_run_telemetry")
    @patch("gavel_ai.core.workflows.oneshot.get_metadata_collector")
    @patch("gavel_ai.core.workflows.oneshot.reset_telemetry")
    @patch("gavel_ai.core.workflows.oneshot.reset_metadata_collector")
    @patch("gavel_ai.core.workflows.oneshot.LocalRunContext")
    async def test_execute_resets_telemetry_on_error(
        self,
        mock_run_context_class,
        mock_reset_metadata,
        mock_reset_telemetry,
        mock_get_metadata,
        mock_configure_telemetry,
        mock_logger: logging.Logger,
    ):
        """execute() resets telemetry and metadata even on error."""
        mock_eval_ctx = MagicMock()
        mock_eval_ctx.eval_name = "test_eval"

        mock_run_ctx = MagicMock()
        mock_run_ctx.run_id = "run-123"
        mock_run_ctx.run_logger = mock_logger
        mock_run_context_class.return_value = mock_run_ctx

        mock_metadata = MagicMock()
        mock_get_metadata.return_value = mock_metadata

        workflow = OneShotWorkflow(mock_eval_ctx, mock_logger)
        workflow._execute_steps = AsyncMock(side_effect=ValueError("Test error"))

        with pytest.raises(ValueError):
            await workflow.execute()

        mock_reset_telemetry.assert_called_once()
        mock_reset_metadata.assert_called_once()

    @pytest.mark.asyncio
    @patch("gavel_ai.core.workflows.oneshot.ValidatorStep")
    @patch("gavel_ai.core.workflows.oneshot.ScenarioProcessorStep")
    @patch("gavel_ai.core.workflows.oneshot.JudgeRunnerStep")
    @patch("gavel_ai.core.workflows.oneshot.ReportRunnerStep")
    async def test_execute_steps_creates_all_steps(
        self,
        mock_report_step_class,
        mock_judge_step_class,
        mock_processor_step_class,
        mock_validator_step_class,
        mock_logger: logging.Logger,
    ):
        """_execute_steps creates all four workflow steps."""
        mock_eval_ctx = MagicMock()
        mock_eval_ctx.eval_name = "test_eval"

        # Mock step instances
        mock_validator = MagicMock()
        mock_validator.phase.value = "validation"
        mock_validator.safe_execute = AsyncMock(return_value=True)
        mock_validator_step_class.return_value = mock_validator

        mock_processor = MagicMock()
        mock_processor.phase.value = "processing"
        mock_processor.safe_execute = AsyncMock(return_value=True)
        mock_processor_step_class.return_value = mock_processor

        mock_judge = MagicMock()
        mock_judge.phase.value = "judging"
        mock_judge.safe_execute = AsyncMock(return_value=True)
        mock_judge_step_class.return_value = mock_judge

        mock_reporter = MagicMock()
        mock_reporter.phase.value = "reporting"
        mock_reporter.safe_execute = AsyncMock(return_value=True)
        mock_report_step_class.return_value = mock_reporter

        mock_run_ctx = MagicMock()

        workflow = OneShotWorkflow(mock_eval_ctx, mock_logger)
        await workflow._execute_steps(mock_run_ctx)

        mock_validator_step_class.assert_called_once_with(mock_logger)
        mock_processor_step_class.assert_called_once_with(mock_logger)
        mock_judge_step_class.assert_called_once_with(mock_logger)
        mock_report_step_class.assert_called_once_with(mock_logger)

    @pytest.mark.asyncio
    @patch("gavel_ai.core.workflows.oneshot.ValidatorStep")
    @patch("gavel_ai.core.workflows.oneshot.ScenarioProcessorStep")
    @patch("gavel_ai.core.workflows.oneshot.JudgeRunnerStep")
    @patch("gavel_ai.core.workflows.oneshot.ReportRunnerStep")
    async def test_execute_steps_runs_steps_in_order(
        self,
        mock_report_step_class,
        mock_judge_step_class,
        mock_processor_step_class,
        mock_validator_step_class,
        mock_logger: logging.Logger,
    ):
        """_execute_steps executes steps in correct order."""
        mock_eval_ctx = MagicMock()
        mock_eval_ctx.eval_name = "test_eval"

        execution_order = []

        # Mock step instances that track execution order
        mock_validator = MagicMock()
        mock_validator.phase.value = "validation"
        mock_validator.safe_execute = AsyncMock(
            side_effect=lambda ctx: execution_order.append("validator") or True
        )
        mock_validator_step_class.return_value = mock_validator

        mock_processor = MagicMock()
        mock_processor.phase.value = "processing"
        mock_processor.safe_execute = AsyncMock(
            side_effect=lambda ctx: execution_order.append("processor") or True
        )
        mock_processor_step_class.return_value = mock_processor

        mock_judge = MagicMock()
        mock_judge.phase.value = "judging"
        mock_judge.safe_execute = AsyncMock(
            side_effect=lambda ctx: execution_order.append("judge") or True
        )
        mock_judge_step_class.return_value = mock_judge

        mock_reporter = MagicMock()
        mock_reporter.phase.value = "reporting"
        mock_reporter.safe_execute = AsyncMock(
            side_effect=lambda ctx: execution_order.append("reporter") or True
        )
        mock_report_step_class.return_value = mock_reporter

        mock_run_ctx = MagicMock()

        workflow = OneShotWorkflow(mock_eval_ctx, mock_logger)
        await workflow._execute_steps(mock_run_ctx)

        assert execution_order == ["validator", "processor", "judge", "reporter"]

    @pytest.mark.asyncio
    @patch("gavel_ai.core.workflows.oneshot.ValidatorStep")
    @patch("gavel_ai.core.workflows.oneshot.ScenarioProcessorStep")
    @patch("gavel_ai.core.workflows.oneshot.JudgeRunnerStep")
    @patch("gavel_ai.core.workflows.oneshot.ReportRunnerStep")
    async def test_execute_steps_raises_processor_error_on_step_failure(
        self,
        mock_report_step_class,
        mock_judge_step_class,
        mock_processor_step_class,
        mock_validator_step_class,
        mock_logger: logging.Logger,
    ):
        """_execute_steps raises ProcessorError if step returns False."""
        mock_eval_ctx = MagicMock()
        mock_eval_ctx.eval_name = "test_eval"

        # Mock validator that fails
        mock_validator = MagicMock()
        mock_validator.phase.value = "validation"
        mock_validator.safe_execute = AsyncMock(return_value=False)
        mock_validator_step_class.return_value = mock_validator

        mock_run_ctx = MagicMock()

        workflow = OneShotWorkflow(mock_eval_ctx, mock_logger)

        with pytest.raises(ProcessorError, match="Step validation failed"):
            await workflow._execute_steps(mock_run_ctx)


class TestProcessorError:
    """Test ProcessorError exception."""

    def test_processor_error_is_exception(self):
        """ProcessorError is an Exception subclass."""
        error = ProcessorError("Test error")
        assert isinstance(error, Exception)

    def test_processor_error_message(self):
        """ProcessorError stores error message."""
        error = ProcessorError("Step failed")
        assert str(error) == "Step failed"
