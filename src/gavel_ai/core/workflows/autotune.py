"""
Autotune workflow orchestrator - pure business logic.

Drives prompt-tuning runs: Prepare (seed runs/<id>/prompts.toml with v1) →
Validate → AutotuneIterationStep (iterate/score/converge/tune loop) → Report.

Completely CLI-agnostic — callable from CLI, API, or scripts. Mirrors the
structure of OneShotWorkflow (core/workflows/oneshot.py).
"""

import logging
from typing import List, Optional

import toml
from dotenv import load_dotenv

from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext
from gavel_ai.core.exceptions import ConfigError, ProcessorError
from gavel_ai.core.steps.autotune_iteration_step import AutotuneIterationStep
from gavel_ai.core.steps.autotune_reporting_step import AutotuneReportingStep
from gavel_ai.core.steps.base import Step
from gavel_ai.core.steps.validator import ValidatorStep
from gavel_ai.telemetry import (
    configure_run_telemetry,
    get_metadata_collector,
    reset_metadata_collector,
    reset_telemetry,
)


class AutotuneWorkflow:
    """
    Pure business logic orchestrator for autotune (prompt meta-optimization) runs.

    This class is completely CLI-agnostic and contains NO typer dependencies.
    It can be called from CLI adapters, HTTP APIs, or scripts.
    """

    def __init__(self, eval_ctx: LocalFileSystemEvalContext, logger: logging.Logger):
        """
        Initialize Autotune workflow.

        Args:
            eval_ctx: Evaluation context with configs and scenarios
            logger: Logger for workflow execution (application-level)
        """
        load_dotenv(verbose=False, override=False)
        self.eval_ctx = eval_ctx
        self.logger = logger
        self.run_ctx: Optional[LocalRunContext] = None

    async def execute(self, resume_run_id: Optional[str] = None) -> LocalRunContext:
        """
        Execute (or resume) an autotune run.

        Args:
            resume_run_id: If provided, resumes an existing run by id — reuses
                its run directory, seeds prior IterationMetadata from completed
                iterations/iteration_N/metadata.json files, and continues from
                the next un-started iteration.

        Returns:
            RunContext with all step outputs populated

        Raises:
            ConfigError: If configuration is invalid (e.g. EvalConfig.tuning unset)
            ValidationError: If validation fails
            ProcessorError: If a workflow step fails
        """
        eval_config = self.eval_ctx.eval_config.read()
        if eval_config.tuning is None:
            raise ConfigError(
                "AutotuneWorkflow requires EvalConfig.tuning to be set for workflow_type='autotune'"
            )

        run_ctx = LocalRunContext(
            eval_ctx=self.eval_ctx,
            base_dir=self.eval_ctx.eval_dir / "runs",
            run_id=resume_run_id,
        )
        self.run_ctx = run_ctx
        run_id = run_ctx.run_id

        configure_run_telemetry(
            run_id=run_id, eval_name=self.eval_ctx.eval_name, base_dir=str(self.eval_ctx.eval_root.parent)
        )

        metadata_collector = get_metadata_collector()
        metadata_collector.record_run_start()

        try:
            verb = "Resuming" if resume_run_id else "Created"
            self.logger.info(f"Running autotune evaluation '{self.eval_ctx.eval_name}'")
            self.logger.info(f"{verb} run: {run_id}")

            start_iteration = self._prepare(run_ctx, resuming=resume_run_id is not None)

            await self._execute_steps(run_ctx, start_iteration)

            self.logger.info(f"Evaluation '{self.eval_ctx.eval_name}' completed successfully")
            return run_ctx

        except Exception as e:
            run_ctx.run_logger.error(f"Execution error: {e}", exc_info=True)
            self.logger.error(f"Execution error: {e}")
            raise

        finally:
            reset_telemetry()
            reset_metadata_collector()

    def _prepare(self, run_ctx: LocalRunContext, resuming: bool) -> int:
        """
        PrepareStep logic: seed runs/<id>/prompts.toml with v1 (the eval's current
        prompt) on first run, and determine the starting iteration for resumes by
        scanning iterations/iteration_N/metadata.json for the last completed round.

        Returns:
            The 1-based iteration number AutotuneIterationStep should start from.
        """
        prompts_toml_path = run_ctx.run_dir / "prompts.toml"
        if not prompts_toml_path.exists():
            eval_config = self.eval_ctx.eval_config.read()
            test_subjects = eval_config.test_subjects
            if not test_subjects:
                raise ConfigError("AutotuneWorkflow requires at least one test_subject in eval_config")

            prompt_name = test_subjects[0].prompt_name or "unknown"
            prompt_ref = prompt_name if ":" in prompt_name else f"{prompt_name}:latest"
            prompt_text = self.eval_ctx.get_prompt(prompt_ref)

            with open(prompts_toml_path, "w", encoding="utf-8") as f:
                toml.dump({"v1": {"prompt": prompt_text}}, f)
            self.logger.info(f"Seeded {prompts_toml_path} with prompt v1 from '{prompt_ref}'")

        if not resuming:
            return 1

        iterations_dir = run_ctx.run_dir / "iterations"
        last_completed = 0
        n = 1
        while (iterations_dir / f"iteration_{n}" / "metadata.json").exists():
            last_completed = n
            n += 1

        start_iteration = last_completed + 1
        self.logger.info(
            f"Resuming run {run_ctx.run_id}: {last_completed} iteration(s) already complete, "
            f"continuing from iteration {start_iteration}"
        )
        return start_iteration

    async def _execute_steps(self, run_ctx: LocalRunContext, start_iteration: int) -> None:
        """
        Execute workflow steps in order: Validate -> AutotuneIterationStep -> Report.

        Raises:
            ProcessorError: If step execution fails
        """
        error_policy = self.eval_ctx.eval_config.read().error_policy

        steps: List[Step] = [
            ValidatorStep(self.logger),
            AutotuneIterationStep(self.logger, start_iteration=start_iteration),
            AutotuneReportingStep(self.logger),
        ]

        for step in steps:
            self.logger.info(f"Running {step.phase.value}...")
            success: bool = await step.safe_execute(run_ctx, error_policy=error_policy)
            if not success:
                err = ProcessorError(f"Step {step.phase.value} failed")
                cause = run_ctx.last_step_error if isinstance(run_ctx.last_step_error, BaseException) else None
                raise err from cause
            self.logger.info(f"Completed {step.phase.value}")


__all__ = ["AutotuneWorkflow"]
