"""
Judge runner step for OneShot workflow.

Responsibilities:
- Extract judges from eval_config.test_subjects[]
- Resolve judge model IDs in agents_config
- Execute JudgeExecutor.execute_batch()
- Store evaluation_results in context

Per Tech Spec 3.9: Extracted from run() lines 247-318.
"""

import logging
from typing import Any, Dict, List

from gavel_ai.core.config_loader import get_model_definition
from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ConfigError
from gavel_ai.core.steps.base import Step, StepPhase
from gavel_ai.judges.judge_executor import JudgeExecutor


class JudgeRunnerStep(Step):
    """
    Executes judges on processor results.

    Sets context.evaluation_results with judge evaluations.
    """

    def __init__(self, logger: logging.Logger):
        super().__init__(logger)

    @property
    def phase(self) -> StepPhase:
        return StepPhase.JUDGING

    async def execute(self, context: RunContext) -> None:  # noqa: C901
        """
        Execute judges on processor results.

        Args:
            context: RunContext with processor_results to evaluate

        Raises:
            ConfigError: If judge configuration fails
        """
        eval_config = context.eval_context.eval_config
        agents_config = context.eval_context.agents_config
        scenarios = context.eval_context.scenarios
        processor_results = context.processor_results

        if processor_results is None:
            raise ConfigError(
                "JudgeRunnerStep requires processor_results - Run ScenarioProcessorStep first"
            )

        test_subject = context.test_subject or "unknown"

        # Extract judges from test_subjects
        judges_list: List[Any] = []
        if eval_config.test_subjects:
            for subject in eval_config.test_subjects:
                if subject.judges:
                    judges_list.extend(subject.judges)

        if not judges_list:
            self.logger.info("No judges configured - skipping judging")
            context.evaluation_results = []
            return

        # Resolve custom model IDs in judge configurations
        for judge_config in judges_list:
            model_to_resolve = None
            if judge_config.config and "model" in judge_config.config:
                model_to_resolve = judge_config.config["model"]
            elif judge_config.model:
                model_to_resolve = judge_config.model

            if model_to_resolve:
                try:
                    model_def = get_model_definition(agents_config, model_to_resolve)
                    resolved_model: str = model_def["model_version"]
                    model_family = model_def["model_family"]

                    judge_config.model = resolved_model
                    if judge_config.config:
                        judge_config.config["model"] = resolved_model
                        judge_config.config["model_family"] = model_family

                    self.logger.debug(
                        f"Resolved judge '{judge_config.name}' model "
                        f"'{model_to_resolve}' to '{resolved_model}'"
                    )
                except ConfigError as e:
                    self.logger.error(
                        f"Failed to resolve model for judge '{judge_config.name}': {e}"
                    )
                    raise

        self.logger.info(f"Running {len(judges_list)} judges on {len(processor_results)} results")

        judge_executor = JudgeExecutor(
            judge_configs=judges_list,
            error_handling="fail_fast",
        )

        # Prepare batch evaluations
        evaluations_batch: List[tuple] = [
            (scenario, str(proc_result.output), "subject_agent")
            for scenario, proc_result in zip(scenarios, processor_results, strict=True)
        ]

        # Execute judges on all results
        evaluation_results = await judge_executor.execute_batch(
            evaluations=evaluations_batch,
            subject_id="PUT",
            test_subject=test_subject,
        )

        # Convert to dict format for storage
        evaluation_results_dicts: List[Dict[str, Any]] = [
            r.model_dump() if hasattr(r, "model_dump") else r for r in evaluation_results
        ]

        context.evaluation_results = evaluation_results_dicts

        self.logger.info(f"Judging complete: {len(evaluation_results)} evaluations")
