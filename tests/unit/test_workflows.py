"""Unit tests for workflow execution framework.

Tests LocalFileSystemEvalContext, LocalRunContext, Step ABC, and StepPhase enum.
"""

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext
from gavel_ai.core.steps.base import DEFAULT_EVAL_ROOT, Step, StepPhase, ValidationResult


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


class TestLocalFileSystemEvalContext:
    """Tests for LocalFileSystemEvalContext class."""

    def test_init(self) -> None:
        """Test EvalContext initialization."""
        ctx = LocalFileSystemEvalContext("test_eval", Path("/tmp/evals"))
        assert ctx.eval_name == "test_eval"
        assert ctx.eval_root == Path("/tmp/evals")

    def test_eval_dir_property(self) -> None:
        """Test eval_dir property."""
        ctx = LocalFileSystemEvalContext("test_eval", Path("/tmp/evals"))
        assert ctx.eval_dir == Path("/tmp/evals/test_eval")

    def test_config_dir_property(self) -> None:
        """Test config_dir property."""
        ctx = LocalFileSystemEvalContext("test_eval", Path("/tmp/evals"))
        assert ctx.config_dir == Path("/tmp/evals/test_eval/config")

    def test_default_eval_root(self) -> None:
        """Test default eval_root is used."""
        ctx = LocalFileSystemEvalContext("test_eval")
        assert ctx.eval_root == Path(DEFAULT_EVAL_ROOT)

    def test_eval_config_lazy_loading(self, tmp_path: Path) -> None:
        """Test that eval_config is lazy-loaded."""
        eval_dir = tmp_path / "test_eval" / "config"
        eval_dir.mkdir(parents=True)

        # Create eval_config.json
        config_data = {
            "eval_name": "test_eval",
            "eval_type": "oneshot",
            "test_subject_type": "local",
            "test_subjects": [{"prompt_name": "default", "judges": []}],
            "variants": ["test"],
            "scenarios": {"source": "file.local", "name": "scenarios.json"},
        }
        with open(eval_dir / "eval_config.json", "w") as f:
            json.dump(config_data, f)

        ctx = LocalFileSystemEvalContext("test_eval", tmp_path)

        # Access should return data source
        data_source = ctx.eval_config
        assert data_source is not None

        # Reading should return config
        config = data_source.read()
        assert config.eval_name == "test_eval"

    def test_agents_config_lazy_loading(self, tmp_path: Path) -> None:
        """Test that agents_config is lazy-loaded."""
        eval_dir = tmp_path / "test_eval" / "config"
        eval_dir.mkdir(parents=True)

        agents_data = {
            "_models": {
                "test_model": {
                    "model_provider": "anthropic",
                    "model_family": "claude",
                    "model_version": "claude-test",
                    "model_parameters": {},
                    "provider_auth": {"api_key": "test"},
                }
            }
        }
        with open(eval_dir / "agents.json", "w") as f:
            json.dump(agents_data, f)

        ctx = LocalFileSystemEvalContext("test_eval", tmp_path)
        agents = ctx.agents.read()

        assert "_models" in agents

    def test_get_prompt_caching(self, tmp_path: Path) -> None:
        """Test that prompts are cached."""
        prompts_dir = tmp_path / "test_eval" / "config" / "prompts"
        prompts_dir.mkdir(parents=True)

        with open(prompts_dir / "default.toml", "w") as f:
            f.write('v1 = "prompt text"')

        ctx = LocalFileSystemEvalContext("test_eval", tmp_path)

        # First access
        result1 = ctx.get_prompt("default:v1")
        assert result1 == "prompt text"

        # Second access should use cache (same result)
        result2 = ctx.get_prompt("default:v1")
        assert result2 == "prompt text"


class TestLocalRunContext:
    """Tests for LocalRunContext class."""

    def test_init(self, tmp_path: Path) -> None:
        """Test RunContext initialization."""
        # Create minimal eval config
        eval_dir = tmp_path / "test_eval" / "config"
        eval_dir.mkdir(parents=True)
        (tmp_path / "test_eval" / "data").mkdir(parents=True)

        config_data = {
            "eval_name": "test_eval",
            "eval_type": "oneshot",
            "test_subject_type": "local",
            "test_subjects": [{"prompt_name": "default", "judges": []}],
            "variants": ["test"],
            "scenarios": {"source": "file.local", "name": "scenarios.json"},
        }
        with open(eval_dir / "eval_config.json", "w") as f:
            json.dump(config_data, f)

        agents_data = {"_models": {}}
        with open(eval_dir / "agents.json", "w") as f:
            json.dump(agents_data, f)

        with open(tmp_path / "test_eval" / "data" / "scenarios.json", "w") as f:
            json.dump([], f)

        eval_ctx = LocalFileSystemEvalContext("test_eval", tmp_path)
        run_ctx = LocalRunContext(eval_ctx, base_dir=tmp_path / "runs", run_id="run-123")

        assert run_ctx.eval_context == eval_ctx
        assert run_ctx.run_id == "run-123"

    def test_run_dir_property(self, tmp_path: Path) -> None:
        """Test run_dir property."""
        eval_dir = tmp_path / "test_eval" / "config"
        eval_dir.mkdir(parents=True)
        (tmp_path / "test_eval" / "data").mkdir(parents=True)

        config_data = {
            "eval_name": "test_eval",
            "eval_type": "oneshot",
            "test_subject_type": "local",
            "test_subjects": [{"prompt_name": "default", "judges": []}],
            "variants": ["test"],
            "scenarios": {"source": "file.local", "name": "scenarios.json"},
        }
        with open(eval_dir / "eval_config.json", "w") as f:
            json.dump(config_data, f)

        agents_data = {"_models": {}}
        with open(eval_dir / "agents.json", "w") as f:
            json.dump(agents_data, f)

        with open(tmp_path / "test_eval" / "data" / "scenarios.json", "w") as f:
            json.dump([], f)

        eval_ctx = LocalFileSystemEvalContext("test_eval", tmp_path)
        run_ctx = LocalRunContext(eval_ctx, base_dir=tmp_path / "runs", run_id="run-123")

        assert run_ctx.run_dir == tmp_path / "runs" / "run-123"


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
            async def execute(self, context) -> None:
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

            async def execute(self, context) -> None:
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

            async def execute(self, context) -> None:
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

            async def execute(self, context) -> None:
                raise ValueError("Test error")

        step = FailingStep(logger)
        mock_context = MagicMock()

        result = await step.safe_execute(mock_context)
        assert result is False
