"""Unit tests for workflow execution framework.

Tests EvalContext, RunContext, Step ABC, and StepPhase enum.
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gavel_ai.core.steps.base import Step, StepPhase, ValidationResult, DEFAULT_EVAL_ROOT
from gavel_ai.core.contexts import EvalContext, RunContext


class TestStepPhase:
    """Tests for StepPhase enum."""

    def test_step_phase_values(self) -> None:
        """Test that all expected phases exist."""
        assert StepPhase.VALIDATION.value == "validation"
        assert StepPhase.SCENARIO_PROCESSING.value == "scenario_processing"
        assert StepPhase.JUDGING.value == "judging"
        assert StepPhase.REPORTING.value == "reporting"

    def test_step_phase_iteration(self) -> None:
        """Test that StepPhase can be iterated."""
        phases = list(StepPhase)
        assert len(phases) == 4


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_valid_result(self) -> None:
        """Test creating a valid result."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_invalid_result_with_errors(self) -> None:
        """Test creating an invalid result with errors."""
        result = ValidationResult(
            is_valid=False, errors=["Error 1", "Error 2"], warnings=["Warning 1"]
        )
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1


class TestEvalContext:
    """Tests for EvalContext class."""

    def test_init(self) -> None:
        """Test EvalContext initialization."""
        ctx = EvalContext("test_eval", Path("/tmp/evals"))
        assert ctx.eval_name == "test_eval"
        assert ctx.eval_root == Path("/tmp/evals")

    def test_eval_dir_property(self) -> None:
        """Test eval_dir property."""
        ctx = EvalContext("test_eval", Path("/tmp/evals"))
        assert ctx.eval_dir == Path("/tmp/evals/test_eval")

    def test_config_dir_property(self) -> None:
        """Test config_dir property."""
        ctx = EvalContext("test_eval", Path("/tmp/evals"))
        assert ctx.config_dir == Path("/tmp/evals/test_eval/config")

    def test_default_eval_root(self) -> None:
        """Test default eval_root is used."""
        ctx = EvalContext("test_eval")
        assert ctx.eval_root == Path(DEFAULT_EVAL_ROOT)

    @patch("gavel_ai.core.workflows.base.ConfigLoader")
    def test_eval_config_lazy_loading(self, mock_loader_class: MagicMock) -> None:
        """Test that eval_config is lazy-loaded."""
        mock_loader = MagicMock()
        mock_loader.load_eval_config.return_value = MagicMock()
        mock_loader_class.return_value = mock_loader

        ctx = EvalContext("test_eval")

        # First access should call loader
        _ = ctx.eval_config
        assert mock_loader.load_eval_config.call_count == 1

        # Second access should use cached value
        _ = ctx.eval_config
        assert mock_loader.load_eval_config.call_count == 1

    @patch("gavel_ai.core.workflows.base.ConfigLoader")
    def test_agents_config_lazy_loading(self, mock_loader_class: MagicMock) -> None:
        """Test that agents_config is lazy-loaded."""
        mock_loader = MagicMock()
        mock_loader.load_agents_config.return_value = {"_models": {}}
        mock_loader_class.return_value = mock_loader

        ctx = EvalContext("test_eval")

        _ = ctx.agents_config
        assert mock_loader.load_agents_config.call_count == 1

        _ = ctx.agents_config
        assert mock_loader.load_agents_config.call_count == 1

    @patch("gavel_ai.core.workflows.base.ConfigLoader")
    def test_scenarios_lazy_loading(self, mock_loader_class: MagicMock) -> None:
        """Test that scenarios is lazy-loaded."""
        mock_loader = MagicMock()
        mock_loader.load_scenarios.return_value = []
        mock_loader_class.return_value = mock_loader

        ctx = EvalContext("test_eval")

        _ = ctx.scenarios
        assert mock_loader.load_scenarios.call_count == 1

        _ = ctx.scenarios
        assert mock_loader.load_scenarios.call_count == 1

    @patch("gavel_ai.core.workflows.base.ConfigLoader")
    def test_get_prompt_caching(self, mock_loader_class: MagicMock) -> None:
        """Test that prompts are cached."""
        mock_loader = MagicMock()
        mock_loader.load_prompt_template.return_value = "prompt text"
        mock_loader_class.return_value = mock_loader

        ctx = EvalContext("test_eval")

        # First access
        result1 = ctx.get_prompt("default:v1")
        assert result1 == "prompt text"
        assert mock_loader.load_prompt_template.call_count == 1

        # Second access should use cache
        result2 = ctx.get_prompt("default:v1")
        assert result2 == "prompt text"
        assert mock_loader.load_prompt_template.call_count == 1


class TestRunContext:
    """Tests for RunContext class."""

    @patch("gavel_ai.core.workflows.base.ConfigLoader")
    @patch("gavel_ai.core.workflows.base.LocalFilesystemRun")
    def test_init(self, mock_run_class: MagicMock, mock_loader_class: MagicMock) -> None:
        """Test RunContext initialization."""
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader

        eval_ctx = EvalContext("test_eval")
        run_ctx = RunContext(eval_ctx, "run-123", base_dir=".gavel")

        assert run_ctx.eval_context == eval_ctx
        assert run_ctx.run_id == "run-123"
        assert run_ctx.base_dir == ".gavel"

    @patch("gavel_ai.core.workflows.base.ConfigLoader")
    @patch("gavel_ai.core.workflows.base.LocalFilesystemRun")
    def test_step_output_properties(
        self, mock_run_class: MagicMock, mock_loader_class: MagicMock
    ) -> None:
        """Test step output properties."""
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader

        eval_ctx = EvalContext("test_eval")
        run_ctx = RunContext(eval_ctx, "run-123")

        # Initial values should be None
        assert run_ctx.validation_result is None
        assert run_ctx.processor_results is None
        assert run_ctx.evaluation_results is None
        assert run_ctx.report_content is None
        assert run_ctx.run_metadata is None

        # Set and verify values
        run_ctx.validation_result = ValidationResult(is_valid=True)
        assert run_ctx.validation_result.is_valid is True

        run_ctx.processor_results = []
        assert run_ctx.processor_results == []

        run_ctx.evaluation_results = [{"score": 8}]
        assert run_ctx.evaluation_results == [{"score": 8}]

        run_ctx.report_content = "<html></html>"
        assert run_ctx.report_content == "<html></html>"

        run_ctx.run_metadata = {"duration": 10.5}
        assert run_ctx.run_metadata == {"duration": 10.5}

    @patch("gavel_ai.core.workflows.base.ConfigLoader")
    @patch("gavel_ai.core.workflows.base.LocalFilesystemRun")
    def test_processing_metadata_properties(
        self, mock_run_class: MagicMock, mock_loader_class: MagicMock
    ) -> None:
        """Test processing metadata properties."""
        mock_loader = MagicMock()
        mock_loader_class.return_value = mock_loader

        eval_ctx = EvalContext("test_eval")
        run_ctx = RunContext(eval_ctx, "run-123")

        assert run_ctx.test_subject is None
        assert run_ctx.model_variant is None

        run_ctx.test_subject = "default:v1"
        run_ctx.model_variant = "claude-sonnet-4-5-20250929"

        assert run_ctx.test_subject == "default:v1"
        assert run_ctx.model_variant == "claude-sonnet-4-5-20250929"


class TestStepABC:
    """Tests for Step abstract base class."""

    def test_step_is_abstract(self) -> None:
        """Test that Step cannot be instantiated directly."""
        logger = logging.getLogger("test")
        with pytest.raises(TypeError):
            Step(logger)  # type: ignore

    def test_concrete_step_must_implement_phase(self) -> None:
        """Test that concrete steps must implement phase property."""
        logger = logging.getLogger("test")

        class IncompleteStep(Step):
            async def execute(self, context: RunContext) -> None:
                pass

        with pytest.raises(TypeError):
            IncompleteStep(logger)  # type: ignore

    def test_concrete_step_must_implement_execute(self) -> None:
        """Test that concrete steps must implement execute method."""
        logger = logging.getLogger("test")

        class IncompleteStep(Step):
            @property
            def phase(self) -> StepPhase:
                return StepPhase.VALIDATION

        with pytest.raises(TypeError):
            IncompleteStep(logger)  # type: ignore

    def test_concrete_step_can_be_instantiated(self) -> None:
        """Test that complete concrete steps can be instantiated."""
        logger = logging.getLogger("test")

        class CompleteStep(Step):
            @property
            def phase(self) -> StepPhase:
                return StepPhase.VALIDATION

            async def execute(self, context: RunContext) -> None:
                pass

        step = CompleteStep(logger)
        assert step.phase == StepPhase.VALIDATION

    @pytest.mark.asyncio
    async def test_safe_execute_returns_true_on_success(self) -> None:
        """Test that safe_execute returns True on successful execution."""
        logger = logging.getLogger("test")

        class SuccessStep(Step):
            @property
            def phase(self) -> StepPhase:
                return StepPhase.VALIDATION

            async def execute(self, context: RunContext) -> None:
                pass

        step = SuccessStep(logger)
        mock_context = MagicMock()

        result = await step.safe_execute(mock_context)
        assert result is True

    @pytest.mark.asyncio
    async def test_safe_execute_returns_false_on_error(self) -> None:
        """Test that safe_execute returns False on error."""
        logger = logging.getLogger("test")

        class FailingStep(Step):
            @property
            def phase(self) -> StepPhase:
                return StepPhase.VALIDATION

            async def execute(self, context: RunContext) -> None:
                raise ValueError("Test error")

        step = FailingStep(logger)
        mock_context = MagicMock()

        result = await step.safe_execute(mock_context)
        assert result is False
