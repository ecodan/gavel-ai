"""Unit tests for workflow step implementations.

Tests ValidatorStep, ScenarioProcessorStep, JudgeRunnerStep, and ReportRunnerStep.
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ConfigError
from gavel_ai.core.steps import (
    JudgeRunnerStep,
    ReportRunnerStep,
    ScenarioProcessorStep,
    ValidatorStep,
)
from gavel_ai.core.steps.base import StepPhase


class TestValidatorStep:
    """Tests for ValidatorStep."""

    def test_phase_is_validation(self) -> None:
        """Test that ValidatorStep has VALIDATION phase."""
        logger = logging.getLogger("test")
        step = ValidatorStep(logger)
        assert step.phase == StepPhase.VALIDATION

    @pytest.mark.asyncio
    async def test_execute_validates_configs(self) -> None:
        """Test that execute validates all configs."""
        logger = logging.getLogger("test")
        step = ValidatorStep(logger)

        # Create mock context with valid config
        mock_eval_config = MagicMock()
        mock_eval_config.test_subjects = [MagicMock()]
        mock_eval_config.variants = ["test_model"]
        mock_eval_config.test_subject_type = "local"

        mock_agents_config = {
            "_models": {"test_model": {"model_version": "gpt-4"}},
        }
        mock_scenarios = [MagicMock()]

        mock_eval_context = MagicMock()
        mock_eval_context.eval_name = "test_eval"
        mock_eval_context.eval_config = mock_eval_config
        mock_eval_context.agents_config = mock_agents_config
        mock_eval_context.scenarios = mock_scenarios

        mock_context = MagicMock(spec=RunContext)
        mock_context.eval_context = mock_eval_context
        mock_context.validation_result = None

        await step.execute(mock_context)

        assert mock_context.validation_result is not None
        assert mock_context.validation_result.is_valid is True

    @pytest.mark.asyncio
    async def test_execute_fails_on_missing_models(self) -> None:
        """Test that execute fails when _models is empty."""
        logger = logging.getLogger("test")
        step = ValidatorStep(logger)

        mock_eval_context = MagicMock()
        mock_eval_context.eval_name = "test_eval"
        mock_eval_context.eval_config = MagicMock()
        mock_eval_context.agents_config = {"_models": {}}

        mock_context = MagicMock(spec=RunContext)
        mock_context.eval_context = mock_eval_context
        mock_context.validation_result = None

        with pytest.raises(ConfigError):
            await step.execute(mock_context)

    @pytest.mark.asyncio
    async def test_execute_fails_on_missing_test_subjects(self) -> None:
        """Test that execute fails when test_subjects is missing."""
        logger = logging.getLogger("test")
        step = ValidatorStep(logger)

        mock_eval_config = MagicMock()
        mock_eval_config.test_subjects = []
        mock_eval_config.variants = ["test_model"]
        mock_eval_config.test_subject_type = "local"

        mock_eval_context = MagicMock()
        mock_eval_context.eval_name = "test_eval"
        mock_eval_context.eval_config = mock_eval_config
        mock_eval_context.agents_config = {
            "_models": {"test_model": {}},
        }

        mock_context = MagicMock(spec=RunContext)
        mock_context.eval_context = mock_eval_context
        mock_context.validation_result = None

        with pytest.raises(ConfigError):
            await step.execute(mock_context)

    @pytest.mark.asyncio
    async def test_execute_passes_with_empty_scenarios(self) -> None:
        """Test that execute passes even when scenarios is empty (not validated anymore)."""
        logger = logging.getLogger("test")
        step = ValidatorStep(logger)

        mock_eval_config = MagicMock()
        mock_eval_config.test_subjects = [MagicMock()]
        mock_eval_config.variants = ["test_model"]
        mock_eval_config.test_subject_type = "local"

        mock_eval_context = MagicMock()
        mock_eval_context.eval_name = "test_eval"
        mock_eval_context.eval_config = mock_eval_config
        mock_eval_context.agents_config = {
            "_models": {"test_model": {"model_version": "gpt-4"}},
        }
        mock_eval_context.scenarios = []

        mock_context = MagicMock(spec=RunContext)
        mock_context.eval_context = mock_eval_context
        mock_context.validation_result = None

        await step.execute(mock_context)

        assert mock_context.validation_result is not None
        assert mock_context.validation_result.is_valid is True


class TestScenarioProcessorStep:
    """Tests for ScenarioProcessorStep."""

    def test_phase_is_scenario_processing(self) -> None:
        """Test that ScenarioProcessorStep has SCENARIO_PROCESSING phase."""
        logger = logging.getLogger("test")
        step = ScenarioProcessorStep(logger)
        assert step.phase == StepPhase.SCENARIO_PROCESSING

    @pytest.mark.asyncio
    @patch("gavel_ai.core.steps.scenario_processor.PromptInputProcessor")
    @patch("gavel_ai.core.steps.scenario_processor.Executor")
    async def test_execute_processes_scenarios(
        self, mock_executor_class: MagicMock, mock_processor_class: MagicMock
    ) -> None:
        """Test that execute processes scenarios."""
        logger = logging.getLogger("test")
        step = ScenarioProcessorStep(logger)

        # Setup mocks
        mock_processor = MagicMock()
        mock_processor_class.return_value = mock_processor

        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(return_value=[MagicMock()])
        mock_executor_class.return_value = mock_executor

        # Create mock context
        mock_async_config = MagicMock()
        mock_async_config.num_workers = 1
        mock_async_config.task_timeout_seconds = 30

        mock_test_subject = MagicMock()
        mock_test_subject.prompt_name = "default:v1"

        mock_eval_config = MagicMock()
        mock_eval_config.test_subject_type = "local"
        mock_eval_config.test_subjects = [mock_test_subject]
        mock_eval_config.variants = ["test_model"]
        mock_eval_config.async_config = mock_async_config

        mock_scenario = MagicMock()
        mock_scenario.scenario_id = "s1"
        mock_scenario.input = "test input"
        mock_scenario.metadata = {}

        mock_eval_context = MagicMock()
        mock_eval_context.eval_name = "test_eval"
        mock_eval_context.eval_config = mock_eval_config
        mock_eval_context.agents_config = {
            "_models": {
                "test_model": {
                    "model_provider": "openai",
                    "model_family": "gpt",
                    "model_version": "gpt-4",
                    "model_parameters": {"temperature": 0.7},
                    "provider_auth": {"api_key": "test-key"},
                }
            },
        }
        mock_eval_context.scenarios = [mock_scenario]

        mock_context = MagicMock(spec=RunContext)
        mock_context.eval_context = mock_eval_context
        mock_context.processor_results = None

        await step.execute(mock_context)

        # Verify processor results were set
        assert mock_context.processor_results is not None
        mock_executor.execute.assert_called_once()


class TestJudgeRunnerStep:
    """Tests for JudgeRunnerStep."""

    def test_phase_is_judging(self) -> None:
        """Test that JudgeRunnerStep has JUDGING phase."""
        logger = logging.getLogger("test")
        step = JudgeRunnerStep(logger)
        assert step.phase == StepPhase.JUDGING

    @pytest.mark.asyncio
    async def test_execute_requires_processor_results(self) -> None:
        """Test that execute fails without processor_results."""
        logger = logging.getLogger("test")
        step = JudgeRunnerStep(logger)

        mock_context = MagicMock(spec=RunContext)
        mock_context.processor_results = None

        with pytest.raises(ConfigError):
            await step.execute(mock_context)

    @pytest.mark.asyncio
    async def test_execute_skips_when_no_judges(self) -> None:
        """Test that execute sets empty results when no judges configured."""
        logger = logging.getLogger("test")
        step = JudgeRunnerStep(logger)

        mock_eval_config = MagicMock()
        mock_eval_config.test_subjects = []

        mock_eval_context = MagicMock()
        mock_eval_context.eval_name = "test_eval"
        mock_eval_context.eval_config = mock_eval_config
        mock_eval_context.agents_config = {"_models": {}}
        mock_eval_context.scenarios = []

        mock_context = MagicMock(spec=RunContext)
        mock_context.eval_context = mock_eval_context
        mock_context.processor_results = []
        mock_context.test_subject = "default:v1"
        mock_context.evaluation_results = None

        await step.execute(mock_context)

        assert mock_context.evaluation_results == []


class TestReportRunnerStep:
    """Tests for ReportRunnerStep."""

    def test_phase_is_reporting(self) -> None:
        """Test that ReportRunnerStep has REPORTING phase."""
        logger = logging.getLogger("test")
        step = ReportRunnerStep(logger)
        assert step.phase == StepPhase.REPORTING

    @pytest.mark.asyncio
    async def test_execute_requires_processor_results(self) -> None:
        """Test that execute fails without processor_results."""
        logger = logging.getLogger("test")
        step = ReportRunnerStep(logger)

        mock_context = MagicMock(spec=RunContext)
        mock_context.processor_results = None

        with pytest.raises(ConfigError):
            await step.execute(mock_context)
