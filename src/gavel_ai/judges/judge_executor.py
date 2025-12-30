"""
Sequential judge executor for gavel-ai.

Orchestrates execution of multiple judges sequentially on processor outputs.
Per Epic 4 Story 4.5: Sequential judge execution with error handling.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from gavel_ai.core.exceptions import JudgeError
from gavel_ai.core.models import (
    EvaluationResult,
    JudgeConfig,
    JudgeEvaluation,
    Scenario,
)
from gavel_ai.judges.base import Judge
from gavel_ai.judges.judge_registry import JudgeRegistry
from gavel_ai.telemetry import get_tracer

logger = logging.getLogger(__name__)


class JudgeExecutor:
    """
    Sequential executor for multiple judges.

    Per Architecture Decision 5: Executes judges sequentially - Judge A evaluates
    all outputs, then Judge B evaluates all outputs, etc. Parallel execution is
    planned for v2+.
    """

    def __init__(
        self,
        judge_configs: List[JudgeConfig],
        error_handling: str = "fail_fast",
    ):
        """
        Initialize judge executor.

        Args:
            judge_configs: List of judge configurations to execute
            error_handling: Error handling strategy ("fail_fast" or "continue_on_error")

        Raises:
            JudgeError: If judge_configs is empty or contains invalid configs
        """
        if not judge_configs:
            raise JudgeError("Judge executor requires at least one judge configuration")

        self.judge_configs = judge_configs
        self.error_handling = error_handling
        self.tracer = get_tracer(__name__)

        # Create judge instances
        self.judges: List[Judge] = []
        for config in judge_configs:
            try:
                judge = JudgeRegistry.create(config)
                self.judges.append(judge)
            except Exception as e:
                raise JudgeError(
                    f"Failed to create judge '{config.judge_id}' of type '{config.judge_type}': {e}"
                ) from e

    async def execute(
        self,
        scenario: Scenario,
        subject_output: str,
        variant_id: str,
        subject_id: str = "put",
        metadata: Optional[dict] = None,
    ) -> EvaluationResult:
        """
        Execute all judges sequentially on a single output.

        Per Epic 4 Story 4.5: Judge A evaluates first, then Judge B, etc.
        All judge results are preserved in the evaluation result.

        Args:
            scenario: The test scenario
            subject_output: The output to evaluate
            variant_id: Model/agent variant identifier
            subject_id: Subject identifier (PUT or SUT)
            metadata: Optional additional metadata

        Returns:
            EvaluationResult with all judge evaluations

        Raises:
            JudgeError: If error_handling is "fail_fast" and a judge fails
        """
        with self.tracer.start_as_current_span("judge_executor.execute") as span:
            span.set_attribute("scenario.id", scenario.id)
            span.set_attribute("variant.id", variant_id)
            span.set_attribute("subject.id", subject_id)
            span.set_attribute("judges.count", len(self.judges))

            judge_evaluations: List[JudgeEvaluation] = []

            # Execute judges sequentially
            for judge in self.judges:
                try:
                    logger.info(
                        f"Executing judge '{judge.config.judge_id}' for scenario '{scenario.id}'"
                    )

                    # Evaluate with the judge
                    result = await judge.evaluate(scenario, subject_output)

                    # Store evaluation
                    evaluation = JudgeEvaluation(
                        judge_id=judge.config.judge_id,
                        score=result.score,
                        reasoning=result.reasoning,
                        evidence=result.evidence,
                    )
                    judge_evaluations.append(evaluation)

                    logger.info(
                        f"Judge '{judge.config.judge_id}' scored {result.score}/10 for scenario '{scenario.id}'"
                    )

                except Exception as e:
                    error_msg = f"Judge '{judge.config.judge_id}' failed for scenario '{scenario.id}': {e}"

                    if self.error_handling == "fail_fast":
                        logger.error(error_msg)
                        raise JudgeError(error_msg) from e
                    else:
                        # Continue on error - log and skip this judge
                        logger.warning(f"{error_msg} - Continuing with next judge")
                        continue

            # Create evaluation result
            timestamp = datetime.now(timezone.utc).isoformat()
            result = EvaluationResult(
                scenario_id=scenario.id,
                variant_id=variant_id,
                subject_id=subject_id,
                scenario_input=scenario.input,
                expected_behavior=scenario.expected_behavior,
                processor_output=subject_output,
                judges=judge_evaluations,
                timestamp=timestamp,
                metadata=metadata or {},
            )

            span.set_attribute("judges.completed", len(judge_evaluations))
            return result

    async def execute_batch(
        self,
        evaluations: List[tuple[Scenario, str, str]],
        subject_id: str = "put",
        metadata: Optional[dict] = None,
    ) -> List[EvaluationResult]:
        """
        Execute all judges on a batch of outputs.

        Per Epic 4 Story 4.5: Each judge evaluates all outputs before the next
        judge starts. This ensures consistent sequential execution.

        Args:
            evaluations: List of (scenario, subject_output, variant_id) tuples
            subject_id: Subject identifier (PUT or SUT)
            metadata: Optional additional metadata

        Returns:
            List of EvaluationResults, one per input

        Raises:
            JudgeError: If error_handling is "fail_fast" and a judge fails
        """
        with self.tracer.start_as_current_span("judge_executor.execute_batch") as span:
            span.set_attribute("batch.size", len(evaluations))
            span.set_attribute("judges.count", len(self.judges))

            results: List[EvaluationResult] = []

            for scenario, subject_output, variant_id in evaluations:
                result = await self.execute(
                    scenario=scenario,
                    subject_output=subject_output,
                    variant_id=variant_id,
                    subject_id=subject_id,
                    metadata=metadata,
                )
                results.append(result)

            span.set_attribute("results.count", len(results))
            return results
