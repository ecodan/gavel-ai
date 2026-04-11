"""
OneShot workflow orchestrator - pure business logic.

This module contains the core OneShot evaluation workflow orchestration.
It is completely CLI-agnostic and can be called from CLI, API, or scripts.

Responsibilities:
- Create RunContext and manage run lifecycle
- Configure telemetry and metadata collection
- Orchestrate step execution (validation → processing → judging → reporting)
- Handle errors and cleanup
- Return populated RunContext with all step outputs
"""

import logging
from pathlib import Path
from typing import List

from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext
from gavel_ai.core.steps.base import Step
from gavel_ai.core.steps.judge_runner import JudgeRunnerStep
from gavel_ai.core.steps.report_runner import ReportRunnerStep
from gavel_ai.core.steps.scenario_processor import ScenarioProcessorStep
from gavel_ai.core.steps.validator import ValidatorStep
from gavel_ai.telemetry import (
    configure_run_telemetry,
    get_metadata_collector,
    reset_metadata_collector,
    reset_telemetry,
)


class ProcessorError(Exception):
    """Raised when a workflow step fails."""

    pass


class OneShotWorkflow:
    """
    Pure business logic orchestrator for OneShot evaluations.

    This class is completely CLI-agnostic and contains NO typer dependencies.
    It can be called from CLI adapters, HTTP APIs, or scripts.
    """

    def __init__(self, eval_ctx: LocalFileSystemEvalContext, logger: logging.Logger):
        """
        Initialize OneShot workflow.

        Args:
            eval_ctx: Evaluation context with configs and scenarios
            logger: Logger for workflow execution (application-level)
        """
        self.eval_ctx = eval_ctx
        self.logger = logger

    async def execute(self) -> LocalRunContext:
        """
        Execute OneShot workflow - orchestrates validator → processor → judge → reporter steps.

        Returns:
            RunContext with all step outputs populated

        Raises:
            ConfigError: If configuration is invalid
            ValidationError: If validation fails
            ProcessorError: If a workflow step fails
        """
        # Create run context - generates run_id and sets up artifacts
        run_ctx = LocalRunContext(
            eval_ctx=self.eval_ctx, base_dir=self.eval_ctx.eval_dir / "runs"
        )
        run_id = run_ctx.run_id

        # Run context automatically:
        # - Initializes artifact DataSources
        # - Configures run logger
        # - Snapshots configs for reproducibility

        # Configure telemetry (OpenTelemetry exporter)
        telemetry_path = configure_run_telemetry(
            run_id=run_id, eval_name=self.eval_ctx.eval_name, base_dir=str(self.eval_ctx.eval_root.parent)
        )

        # Initialize metadata collector
        metadata_collector = get_metadata_collector()
        metadata_collector.record_run_start()

        try:
            self.logger.info(f"Running oneshot evaluation '{self.eval_ctx.eval_name}'")
            self.logger.info(f"Created run: {run_id}")

            # Create and execute steps
            await self._execute_steps(run_ctx)

            # Success logging
            self.logger.info(f"Evaluation '{self.eval_ctx.eval_name}' completed successfully")

            return run_ctx

        except Exception as e:
            run_ctx.run_logger.error(f"Execution error: {e}", exc_info=True)
            self.logger.error(f"Execution error: {e}", exc_info=True)
            raise

        finally:
            # Always reset telemetry and metadata after run completes
            reset_telemetry()
            reset_metadata_collector()

    async def _execute_steps(self, run_ctx: LocalRunContext) -> None:
        """
        Execute workflow steps in order.

        Args:
            run_ctx: Run context to populate with step outputs

        Raises:
            ProcessorError: If step execution fails
        """
        # Create steps (pass application logger for class-level logging)
        steps: List[Step] = [
            ValidatorStep(self.logger),
            ScenarioProcessorStep(self.logger),
            JudgeRunnerStep(self.logger),
            ReportRunnerStep(self.logger),
        ]

        # Execute steps in order
        for step in steps:
            self.logger.info(f"Running {step.phase.value}...")
            success: bool = await step.safe_execute(run_ctx)
            if not success:
                raise ProcessorError(f"Step {step.phase.value} failed")
            self.logger.info(f"Completed {step.phase.value}")
