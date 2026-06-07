"""Unit tests for AutotuneWorkflow orchestrator: telemetry lifecycle, _prepare
(prompt seeding + resume scanning), and _execute_steps ordering/error handling."""

import json
import logging
from pathlib import Path
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import toml

from gavel_ai.core.exceptions import ConfigError, ProcessorError
from gavel_ai.core.workflows.autotune import AutotuneWorkflow
from gavel_ai.models.config import (
    EvalConfig,
    JudgeConfig,
    ScenariosConfig,
    TestSubject,
    TuningConfig,
)

pytestmark = pytest.mark.unit


def _make_tuning_config(**overrides: Any) -> TuningConfig:
    base = {
        "max_rounds": 5,
        "convergence_threshold": 0.02,
        "target_score": None,
        "degradation_tolerance": 0.05,
        "tuning_agent_model": "claude-standard",
        "tuning_agent_temperature": 0.7,
    }
    base.update(overrides)
    return TuningConfig(**base)


def _make_eval_config(tuning: Optional[TuningConfig], prompt_name: str = "assistant") -> EvalConfig:
    return EvalConfig(
        eval_type="oneshot",
        eval_name="test_eval",
        test_subject_type="local",
        test_subjects=[
            TestSubject(
                prompt_name=prompt_name,
                judges=[JudgeConfig(name="similarity", type="deepeval.geval")],
            )
        ],
        variants=["model-a"],
        scenarios=ScenariosConfig(source="file.local", name="scenarios.json"),
        workflow_type="autotune",
        tuning=tuning,
    )


def _make_eval_ctx(tmp_path: Path, eval_config: EvalConfig, prompt_text: str = "Answer: {{input}}") -> MagicMock:
    eval_ctx = MagicMock()
    eval_ctx.eval_name = "test_eval"
    eval_ctx.eval_dir = tmp_path / "eval"
    eval_ctx.eval_root = tmp_path / ".gavel" / "evaluations"
    eval_ctx.eval_config.read.return_value = eval_config
    eval_ctx.get_prompt.return_value = prompt_text
    return eval_ctx


class TestInit:
    def test_init_stores_eval_ctx_and_logger(self, mock_logger: logging.Logger) -> None:
        eval_ctx = MagicMock()
        workflow = AutotuneWorkflow(eval_ctx, mock_logger)

        assert workflow.eval_ctx == eval_ctx
        assert workflow.logger == mock_logger
        assert workflow.run_ctx is None


class TestExecute:
    @pytest.mark.asyncio
    async def test_raises_config_error_when_tuning_not_configured(
        self, mock_logger: logging.Logger, tmp_path: Path
    ) -> None:
        eval_config = _make_eval_config(tuning=None)
        eval_ctx = _make_eval_ctx(tmp_path, eval_config)

        workflow = AutotuneWorkflow(eval_ctx, mock_logger)

        with pytest.raises(ConfigError, match="EvalConfig.tuning"):
            await workflow.execute()

    @pytest.mark.asyncio
    @patch("gavel_ai.core.workflows.autotune.configure_run_telemetry")
    @patch("gavel_ai.core.workflows.autotune.get_metadata_collector")
    @patch("gavel_ai.core.workflows.autotune.reset_telemetry")
    @patch("gavel_ai.core.workflows.autotune.reset_metadata_collector")
    @patch("gavel_ai.core.workflows.autotune.LocalRunContext")
    async def test_execute_creates_run_context_runs_steps_and_returns_it(
        self,
        mock_run_context_class: MagicMock,
        mock_reset_metadata: MagicMock,
        mock_reset_telemetry: MagicMock,
        mock_get_metadata: MagicMock,
        mock_configure_telemetry: MagicMock,
        mock_logger: logging.Logger,
        tmp_path: Path,
    ) -> None:
        eval_config = _make_eval_config(tuning=_make_tuning_config())
        eval_ctx = _make_eval_ctx(tmp_path, eval_config)

        run_dir = tmp_path / "runs" / "run-123"
        run_dir.mkdir(parents=True)
        mock_run_ctx = MagicMock()
        mock_run_ctx.run_id = "run-123"
        mock_run_ctx.run_dir = run_dir
        mock_run_ctx.run_logger = mock_logger
        mock_run_context_class.return_value = mock_run_ctx

        mock_metadata = MagicMock()
        mock_get_metadata.return_value = mock_metadata

        workflow = AutotuneWorkflow(eval_ctx, mock_logger)
        workflow._execute_steps = AsyncMock()

        result = await workflow.execute()

        mock_run_context_class.assert_called_once_with(
            eval_ctx=eval_ctx, base_dir=eval_ctx.eval_dir / "runs", run_id=None
        )
        mock_configure_telemetry.assert_called_once_with(
            run_id="run-123", eval_name="test_eval", base_dir=str(eval_ctx.eval_root.parent)
        )
        mock_metadata.record_run_start.assert_called_once()
        workflow._execute_steps.assert_called_once()
        assert workflow._execute_steps.call_args.args[0] == mock_run_ctx
        assert result == mock_run_ctx
        mock_reset_telemetry.assert_called_once()
        mock_reset_metadata.assert_called_once()

    @pytest.mark.asyncio
    @patch("gavel_ai.core.workflows.autotune.configure_run_telemetry")
    @patch("gavel_ai.core.workflows.autotune.get_metadata_collector")
    @patch("gavel_ai.core.workflows.autotune.reset_telemetry")
    @patch("gavel_ai.core.workflows.autotune.reset_metadata_collector")
    @patch("gavel_ai.core.workflows.autotune.LocalRunContext")
    async def test_execute_resets_telemetry_on_step_error(
        self,
        mock_run_context_class: MagicMock,
        mock_reset_metadata: MagicMock,
        mock_reset_telemetry: MagicMock,
        mock_get_metadata: MagicMock,
        mock_configure_telemetry: MagicMock,
        mock_logger: logging.Logger,
        tmp_path: Path,
    ) -> None:
        eval_config = _make_eval_config(tuning=_make_tuning_config())
        eval_ctx = _make_eval_ctx(tmp_path, eval_config)

        run_dir = tmp_path / "runs" / "run-123"
        run_dir.mkdir(parents=True)
        mock_run_ctx = MagicMock()
        mock_run_ctx.run_id = "run-123"
        mock_run_ctx.run_dir = run_dir
        mock_run_ctx.run_logger = mock_logger
        mock_run_context_class.return_value = mock_run_ctx

        mock_get_metadata.return_value = MagicMock()

        workflow = AutotuneWorkflow(eval_ctx, mock_logger)
        workflow._execute_steps = AsyncMock(side_effect=ProcessorError("boom"))

        with pytest.raises(ProcessorError, match="boom"):
            await workflow.execute()

        mock_reset_telemetry.assert_called_once()
        mock_reset_metadata.assert_called_once()

    @pytest.mark.asyncio
    @patch("gavel_ai.core.workflows.autotune.configure_run_telemetry")
    @patch("gavel_ai.core.workflows.autotune.get_metadata_collector")
    @patch("gavel_ai.core.workflows.autotune.reset_telemetry")
    @patch("gavel_ai.core.workflows.autotune.reset_metadata_collector")
    @patch("gavel_ai.core.workflows.autotune.LocalRunContext")
    async def test_execute_passes_resume_run_id_through(
        self,
        mock_run_context_class: MagicMock,
        mock_reset_metadata: MagicMock,
        mock_reset_telemetry: MagicMock,
        mock_get_metadata: MagicMock,
        mock_configure_telemetry: MagicMock,
        mock_logger: logging.Logger,
        tmp_path: Path,
    ) -> None:
        eval_config = _make_eval_config(tuning=_make_tuning_config())
        eval_ctx = _make_eval_ctx(tmp_path, eval_config)

        run_dir = tmp_path / "runs" / "run-existing"
        run_dir.mkdir(parents=True)
        # prompts.toml already present so _prepare doesn't try to resolve a real prompt
        toml.dump({"v1": {"prompt": "Answer: {{input}}"}}, open(run_dir / "prompts.toml", "w"))

        mock_run_ctx = MagicMock()
        mock_run_ctx.run_id = "run-existing"
        mock_run_ctx.run_dir = run_dir
        mock_run_ctx.run_logger = mock_logger
        mock_run_context_class.return_value = mock_run_ctx

        mock_get_metadata.return_value = MagicMock()

        workflow = AutotuneWorkflow(eval_ctx, mock_logger)
        workflow._execute_steps = AsyncMock()

        await workflow.execute(resume_run_id="run-existing")

        mock_run_context_class.assert_called_once_with(
            eval_ctx=eval_ctx, base_dir=eval_ctx.eval_dir / "runs", run_id="run-existing"
        )


class TestPrepare:
    def _make_run_ctx(self, tmp_path: Path, run_id: str = "run-001") -> MagicMock:
        run_dir = tmp_path / "runs" / run_id
        run_dir.mkdir(parents=True)
        run_ctx = MagicMock()
        run_ctx.run_id = run_id
        run_ctx.run_dir = run_dir
        return run_ctx

    def test_seeds_prompts_toml_with_v1_when_absent(
        self, mock_logger: logging.Logger, tmp_path: Path
    ) -> None:
        eval_config = _make_eval_config(tuning=_make_tuning_config(), prompt_name="assistant")
        eval_ctx = _make_eval_ctx(tmp_path, eval_config, prompt_text="You are a helpful assistant.")
        run_ctx = self._make_run_ctx(tmp_path)

        workflow = AutotuneWorkflow(eval_ctx, mock_logger)
        start_iteration = workflow._prepare(run_ctx, resuming=False)

        assert start_iteration == 1
        prompts_toml_path = run_ctx.run_dir / "prompts.toml"
        assert prompts_toml_path.exists()
        data = toml.load(str(prompts_toml_path))
        assert data == {"v1": {"prompt": "You are a helpful assistant."}}
        eval_ctx.get_prompt.assert_called_once_with("assistant:latest")

    def test_uses_explicit_version_in_prompt_ref_when_present(
        self, mock_logger: logging.Logger, tmp_path: Path
    ) -> None:
        eval_config = _make_eval_config(tuning=_make_tuning_config(), prompt_name="assistant:v3")
        eval_ctx = _make_eval_ctx(tmp_path, eval_config, prompt_text="Pinned prompt text")
        run_ctx = self._make_run_ctx(tmp_path)

        workflow = AutotuneWorkflow(eval_ctx, mock_logger)
        workflow._prepare(run_ctx, resuming=False)

        eval_ctx.get_prompt.assert_called_once_with("assistant:v3")

    def test_does_not_overwrite_existing_prompts_toml(
        self, mock_logger: logging.Logger, tmp_path: Path
    ) -> None:
        eval_config = _make_eval_config(tuning=_make_tuning_config())
        eval_ctx = _make_eval_ctx(tmp_path, eval_config)
        run_ctx = self._make_run_ctx(tmp_path)

        existing = {"v1": {"prompt": "Already seeded"}, "v2": {"prompt": "Tuned version"}}
        toml.dump(existing, open(run_ctx.run_dir / "prompts.toml", "w"))

        workflow = AutotuneWorkflow(eval_ctx, mock_logger)
        workflow._prepare(run_ctx, resuming=False)

        data = toml.load(str(run_ctx.run_dir / "prompts.toml"))
        assert data == existing
        eval_ctx.get_prompt.assert_not_called()

    def test_fresh_run_starts_at_iteration_one(
        self, mock_logger: logging.Logger, tmp_path: Path
    ) -> None:
        eval_config = _make_eval_config(tuning=_make_tuning_config())
        eval_ctx = _make_eval_ctx(tmp_path, eval_config)
        run_ctx = self._make_run_ctx(tmp_path)

        workflow = AutotuneWorkflow(eval_ctx, mock_logger)
        assert workflow._prepare(run_ctx, resuming=False) == 1

    def test_resume_scans_completed_iterations_and_continues_after_last(
        self, mock_logger: logging.Logger, tmp_path: Path
    ) -> None:
        eval_config = _make_eval_config(tuning=_make_tuning_config())
        eval_ctx = _make_eval_ctx(tmp_path, eval_config)
        run_ctx = self._make_run_ctx(tmp_path, run_id="run-resume")
        toml.dump({"v1": {"prompt": "x"}}, open(run_ctx.run_dir / "prompts.toml", "w"))

        iterations_dir = run_ctx.run_dir / "iterations"
        for n in (1, 2):
            iter_dir = iterations_dir / f"iteration_{n}"
            iter_dir.mkdir(parents=True)
            (iter_dir / "metadata.json").write_text(json.dumps({"iteration": n}), encoding="utf-8")
        # iteration 3 started but never completed (no metadata.json) - must not count
        (iterations_dir / "iteration_3").mkdir(parents=True)

        workflow = AutotuneWorkflow(eval_ctx, mock_logger)
        assert workflow._prepare(run_ctx, resuming=True) == 3

    def test_resume_with_no_completed_iterations_starts_at_one(
        self, mock_logger: logging.Logger, tmp_path: Path
    ) -> None:
        eval_config = _make_eval_config(tuning=_make_tuning_config())
        eval_ctx = _make_eval_ctx(tmp_path, eval_config)
        run_ctx = self._make_run_ctx(tmp_path, run_id="run-resume-empty")
        toml.dump({"v1": {"prompt": "x"}}, open(run_ctx.run_dir / "prompts.toml", "w"))

        workflow = AutotuneWorkflow(eval_ctx, mock_logger)
        assert workflow._prepare(run_ctx, resuming=True) == 1

    def test_raises_config_error_when_no_test_subjects(
        self, mock_logger: logging.Logger, tmp_path: Path
    ) -> None:
        eval_config = _make_eval_config(tuning=_make_tuning_config())
        eval_config.test_subjects = []
        eval_ctx = _make_eval_ctx(tmp_path, eval_config)
        run_ctx = self._make_run_ctx(tmp_path)

        workflow = AutotuneWorkflow(eval_ctx, mock_logger)

        with pytest.raises(ConfigError, match="test_subject"):
            workflow._prepare(run_ctx, resuming=False)


class TestExecuteSteps:
    @pytest.mark.asyncio
    @patch("gavel_ai.core.workflows.autotune.AutotuneReportingStep")
    @patch("gavel_ai.core.workflows.autotune.AutotuneIterationStep")
    @patch("gavel_ai.core.workflows.autotune.ValidatorStep")
    async def test_creates_and_runs_steps_in_order(
        self,
        mock_validator_class: MagicMock,
        mock_iteration_class: MagicMock,
        mock_reporting_class: MagicMock,
        mock_logger: logging.Logger,
        tmp_path: Path,
    ) -> None:
        eval_config = _make_eval_config(tuning=_make_tuning_config())
        eval_ctx = _make_eval_ctx(tmp_path, eval_config)

        execution_order = []

        mock_validator = MagicMock()
        mock_validator.phase.value = "validation"
        mock_validator.safe_execute = AsyncMock(side_effect=lambda ctx, **kw: execution_order.append("validator") or True)
        mock_validator_class.return_value = mock_validator

        mock_iteration = MagicMock()
        mock_iteration.phase.value = "autotune_iteration"
        mock_iteration.safe_execute = AsyncMock(side_effect=lambda ctx, **kw: execution_order.append("iteration") or True)
        mock_iteration_class.return_value = mock_iteration

        mock_reporting = MagicMock()
        mock_reporting.phase.value = "reporting"
        mock_reporting.safe_execute = AsyncMock(side_effect=lambda ctx, **kw: execution_order.append("reporting") or True)
        mock_reporting_class.return_value = mock_reporting

        mock_run_ctx = MagicMock()

        workflow = AutotuneWorkflow(eval_ctx, mock_logger)
        await workflow._execute_steps(mock_run_ctx, start_iteration=1)

        mock_validator_class.assert_called_once_with(mock_logger)
        mock_iteration_class.assert_called_once_with(mock_logger, start_iteration=1)
        mock_reporting_class.assert_called_once_with(mock_logger)
        assert execution_order == ["validator", "iteration", "reporting"]

    @pytest.mark.asyncio
    @patch("gavel_ai.core.workflows.autotune.AutotuneReportingStep")
    @patch("gavel_ai.core.workflows.autotune.AutotuneIterationStep")
    @patch("gavel_ai.core.workflows.autotune.ValidatorStep")
    async def test_passes_start_iteration_through_to_iteration_step(
        self,
        mock_validator_class: MagicMock,
        mock_iteration_class: MagicMock,
        mock_reporting_class: MagicMock,
        mock_logger: logging.Logger,
        tmp_path: Path,
    ) -> None:
        eval_config = _make_eval_config(tuning=_make_tuning_config())
        eval_ctx = _make_eval_ctx(tmp_path, eval_config)

        for mock_class in (mock_validator_class, mock_iteration_class, mock_reporting_class):
            instance = MagicMock()
            instance.phase.value = "phase"
            instance.safe_execute = AsyncMock(return_value=True)
            mock_class.return_value = instance

        mock_run_ctx = MagicMock()

        workflow = AutotuneWorkflow(eval_ctx, mock_logger)
        await workflow._execute_steps(mock_run_ctx, start_iteration=4)

        mock_iteration_class.assert_called_once_with(mock_logger, start_iteration=4)

    @pytest.mark.asyncio
    @patch("gavel_ai.core.workflows.autotune.AutotuneReportingStep")
    @patch("gavel_ai.core.workflows.autotune.AutotuneIterationStep")
    @patch("gavel_ai.core.workflows.autotune.ValidatorStep")
    async def test_raises_processor_error_on_step_failure(
        self,
        mock_validator_class: MagicMock,
        mock_iteration_class: MagicMock,
        mock_reporting_class: MagicMock,
        mock_logger: logging.Logger,
        tmp_path: Path,
    ) -> None:
        eval_config = _make_eval_config(tuning=_make_tuning_config())
        eval_ctx = _make_eval_ctx(tmp_path, eval_config)

        mock_validator = MagicMock()
        mock_validator.phase.value = "validation"
        mock_validator.safe_execute = AsyncMock(return_value=False)
        mock_validator_class.return_value = mock_validator

        mock_run_ctx = MagicMock()
        mock_run_ctx.last_step_error = RuntimeError("validation blew up")

        workflow = AutotuneWorkflow(eval_ctx, mock_logger)

        with pytest.raises(ProcessorError, match="Step validation failed"):
            await workflow._execute_steps(mock_run_ctx, start_iteration=1)
