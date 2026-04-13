import pytest

pytestmark = pytest.mark.unit
"""Unit tests for workflow step implementations.

Tests ValidatorStep, ScenarioProcessorStep, JudgeRunnerStep, and ReportRunnerStep.
"""

import logging
from unittest.mock import AsyncMock, MagicMock, call, patch

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
from gavel_ai.models.runtime import OutputRecord, ProcessorResult


def _create_mock_data_source(return_value):
    """Create a mock data source that returns the given value from read()."""
    mock_ds = MagicMock()
    mock_ds.read.return_value = return_value
    return mock_ds


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

        # Create mock config data
        mock_eval_config = MagicMock()
        mock_eval_config.test_subjects = [MagicMock()]
        mock_eval_config.variants = ["test_model"]
        mock_eval_config.test_subject_type = "local"

        mock_agents_config = {
            "_models": {"test_model": {"model_version": "gpt-4"}},
        }
        mock_scenarios = [MagicMock()]

        # Create mock eval context with data sources
        mock_eval_context = MagicMock()
        mock_eval_context.eval_name = "test_eval"
        mock_eval_context.eval_config = _create_mock_data_source(mock_eval_config)
        mock_eval_context.agents = _create_mock_data_source(mock_agents_config)
        mock_eval_context.scenarios = _create_mock_data_source(mock_scenarios)

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

        # Create mock config with empty _models
        mock_eval_config = MagicMock()
        mock_eval_config.test_subjects = [MagicMock()]
        mock_eval_config.variants = ["test_model"]
        mock_eval_config.test_subject_type = "local"

        mock_agents_config = {"_models": {}}

        mock_eval_context = MagicMock()
        mock_eval_context.eval_name = "test_eval"
        mock_eval_context.eval_config = _create_mock_data_source(mock_eval_config)
        mock_eval_context.agents = _create_mock_data_source(mock_agents_config)

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

        mock_agents_config = {
            "_models": {"test_model": {}},
        }

        mock_eval_context = MagicMock()
        mock_eval_context.eval_name = "test_eval"
        mock_eval_context.eval_config = _create_mock_data_source(mock_eval_config)
        mock_eval_context.agents = _create_mock_data_source(mock_agents_config)

        mock_context = MagicMock(spec=RunContext)
        mock_context.eval_context = mock_eval_context
        mock_context.validation_result = None

        with pytest.raises(ConfigError):
            await step.execute(mock_context)

    @pytest.mark.asyncio
    async def test_execute_raises_with_empty_scenarios(self) -> None:
        """Test that execute raises ValidationError when scenarios list is empty."""
        from gavel_ai.core.exceptions import ValidationError

        logger = logging.getLogger("test")
        step = ValidatorStep(logger)

        mock_eval_config = MagicMock()
        mock_eval_config.test_subjects = [MagicMock()]
        mock_eval_config.variants = ["test_model"]
        mock_eval_config.test_subject_type = "local"

        mock_agents_config = {
            "_models": {"test_model": {"model_version": "gpt-4"}},
        }

        mock_eval_context = MagicMock()
        mock_eval_context.eval_name = "test_eval"
        mock_eval_context.eval_config = _create_mock_data_source(mock_eval_config)
        mock_eval_context.agents = _create_mock_data_source(mock_agents_config)
        mock_eval_context.scenarios = _create_mock_data_source([])

        mock_context = MagicMock(spec=RunContext)
        mock_context.eval_context = mock_eval_context
        mock_context.validation_result = None

        with pytest.raises(ValidationError, match="No scenarios"):
            await step.execute(mock_context)


def _make_executor_mock_that_calls_callback(proc_results_per_exec):
    """Return an Executor mock whose execute() calls on_result for each ProcessorResult."""

    async def _fake_execute(inputs, on_result=None):
        for input_item, proc_result in zip(inputs, proc_results_per_exec):
            if on_result is not None:
                on_result(input_item, proc_result)

    mock_executor = MagicMock()
    mock_executor.execute = _fake_execute
    return mock_executor


def _base_eval_context(variants=None, num_scenarios=1):
    """Build a reusable mock eval context."""
    variants = variants or ["test_model"]

    mock_async_config = MagicMock()
    mock_async_config.num_workers = 1
    mock_async_config.task_timeout_seconds = 30

    mock_test_subject = MagicMock()
    mock_test_subject.prompt_name = "default:v1"

    mock_eval_config = MagicMock()
    mock_eval_config.test_subject_type = "local"
    mock_eval_config.test_subjects = [mock_test_subject]
    mock_eval_config.variants = variants
    mock_eval_config.async_config = mock_async_config

    scenarios = []
    for i in range(num_scenarios):
        s = MagicMock()
        s.id = f"s{i + 1}"
        s.scenario_id = f"s{i + 1}"
        s.input = f"input {i + 1}"
        s.metadata = {}
        scenarios.append(s)

    agents_config = {
        "_models": {
            "test_model": {
                "model_provider": "openai",
                "model_family": "gpt",
                "model_version": "gpt-4",
                "model_parameters": {"temperature": 0.7},
                "provider_auth": {"api_key": "test-key"},
            },
            "variant_b": {
                "model_provider": "anthropic",
                "model_family": "claude",
                "model_version": "claude-3-5-sonnet",
                "model_parameters": {"temperature": 0.7},
                "provider_auth": {"api_key": "test-key"},
            },
        }
    }

    mock_eval_context = MagicMock()
    mock_eval_context.eval_name = "test_eval"
    mock_eval_context.eval_config = _create_mock_data_source(mock_eval_config)
    mock_eval_context.agents = _create_mock_data_source(agents_config)
    mock_eval_context.scenarios = _create_mock_data_source(scenarios)

    return mock_eval_context, scenarios


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
        """Test that execute processes a single variant and sets processor_results."""
        logger = logging.getLogger("test")
        step = ScenarioProcessorStep(logger)

        mock_processor_class.return_value = MagicMock()
        proc_result = ProcessorResult(output="output1", metadata={})
        mock_executor_class.return_value = _make_executor_mock_that_calls_callback([proc_result])

        mock_eval_context, scenarios = _base_eval_context(variants=["test_model"], num_scenarios=1)

        mock_context = MagicMock(spec=RunContext)
        mock_context.eval_context = mock_eval_context
        mock_context.results_raw = MagicMock()

        await step.execute(mock_context)

        # processor_results should be a list of OutputRecord objects
        assert mock_context.processor_results is not None
        assert len(mock_context.processor_results) == 1
        assert isinstance(mock_context.processor_results[0], OutputRecord)
        assert mock_context.processor_results[0].variant_id == "gpt-4"
        mock_context.results_raw.append.assert_called_once()

    @pytest.mark.asyncio
    @patch("gavel_ai.core.steps.scenario_processor.PromptInputProcessor")
    @patch("gavel_ai.core.steps.scenario_processor.Executor")
    async def test_execute_two_variants_produces_2n_records(
        self, mock_executor_class: MagicMock, mock_processor_class: MagicMock
    ) -> None:
        """Two variants × N scenarios → 2N OutputRecord objects with correct variant_id."""
        logger = logging.getLogger("test")
        step = ScenarioProcessorStep(logger)
        num_scenarios = 3

        mock_processor_class.return_value = MagicMock()
        proc_results = [ProcessorResult(output=f"out{i}", metadata={}) for i in range(num_scenarios)]
        mock_executor_class.return_value = _make_executor_mock_that_calls_callback(proc_results)

        mock_eval_context, scenarios = _base_eval_context(
            variants=["test_model", "variant_b"], num_scenarios=num_scenarios
        )

        mock_context = MagicMock(spec=RunContext)
        mock_context.eval_context = mock_eval_context
        mock_context.results_raw = MagicMock()

        await step.execute(mock_context)

        # 2 variants × 3 scenarios = 6 OutputRecord objects
        assert mock_context.processor_results is not None
        assert len(mock_context.processor_results) == 2 * num_scenarios
        assert all(isinstance(r, OutputRecord) for r in mock_context.processor_results)

        # Each variant's records have distinct variant_id
        variant_ids = {r.variant_id for r in mock_context.processor_results}
        assert len(variant_ids) == 2

        # results_raw.append called 2N times
        assert mock_context.results_raw.append.call_count == 2 * num_scenarios

        # context.model_variant is a comma-joined display string
        assert mock_context.model_variant == "test_model, variant_b"


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

        # Create mock eval context with data sources
        mock_eval_config = MagicMock()
        mock_eval_config.test_subjects = []

        mock_eval_context = MagicMock()
        mock_eval_context.eval_config = _create_mock_data_source(mock_eval_config)
        mock_eval_context.agents = _create_mock_data_source({"_models": {}})
        mock_eval_context.scenarios = _create_mock_data_source([])

        mock_context = MagicMock(spec=RunContext)
        mock_context.eval_context = mock_eval_context
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
        mock_eval_context.eval_config = _create_mock_data_source(mock_eval_config)
        mock_eval_context.agents = _create_mock_data_source({"_models": {}})
        mock_eval_context.scenarios = _create_mock_data_source([])

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

        # Create mock eval context with data sources
        mock_eval_config = MagicMock()
        mock_eval_config.test_subjects = []

        mock_eval_context = MagicMock()
        mock_eval_context.eval_config = _create_mock_data_source(mock_eval_config)
        mock_eval_context.scenarios = _create_mock_data_source([])

        mock_context = MagicMock(spec=RunContext)
        mock_context.eval_context = mock_eval_context
        mock_context.processor_results = None
        mock_context.evaluation_results = None

        with pytest.raises(ConfigError):
            await step.execute(mock_context)
