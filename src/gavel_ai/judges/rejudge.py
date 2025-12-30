"""
Re-judging capability for gavel-ai.

Allows re-evaluating stored results with new or modified judges without
re-running the expensive processor execution.

Per Epic 4 Story 4.7: Fast re-judging using stored processor outputs.
"""

import logging
from pathlib import Path
from typing import List, Optional

from gavel_ai.core.models import (
    EvaluationResult,
    JudgeConfig,
    JudgeEvaluation,
    Scenario,
)
from gavel_ai.core.result_storage import ResultStorage
from gavel_ai.judges.judge_executor import JudgeExecutor
from gavel_ai.telemetry import get_tracer

logger = logging.getLogger(__name__)


class ReJudge:
    """
    Re-judging engine for stored evaluation results.

    Per Epic 4 Story 4.7: Enables iterating on judge definitions without
    expensive API calls to processors. Re-executes judges on stored
    processor outputs.
    """

    def __init__(
        self,
        results_file: Path,
        judge_configs: List[JudgeConfig],
        error_handling: str = "fail_fast",
    ):
        """
        Initialize re-judging engine.

        Args:
            results_file: Path to existing results.jsonl
            judge_configs: List of judge configurations to apply
            error_handling: Error handling strategy ("fail_fast" or "continue_on_error")
        """
        self.storage = ResultStorage(results_file)
        self.judge_executor = JudgeExecutor(judge_configs, error_handling)
        self.tracer = get_tracer(__name__)

    async def rejudge_all(
        self,
        preserve_existing: bool = True,
        output_file: Optional[Path] = None,
    ) -> List[EvaluationResult]:
        """
        Re-judge all stored results with current judge configuration.

        Per Epic 4 Story 4.7: Re-evaluates all results without re-running
        processors. Old judge results are preserved and new results added.

        Args:
            preserve_existing: If True, preserve existing judge evaluations
            output_file: Optional path to write re-judged results (default: same file)

        Returns:
            List of updated EvaluationResults with new judge evaluations

        Raises:
            IOError: If unable to read/write results
        """
        with self.tracer.start_as_current_span("rejudge.rejudge_all") as span:
            logger.info("Starting re-judging of all stored results")

            # Load existing results
            existing_results = self.storage.load_all()
            span.set_attribute("results.count", len(existing_results))

            if not existing_results:
                logger.warning("No existing results found to re-judge")
                return []

            # Re-judge each result
            rejudged_results: List[EvaluationResult] = []

            for existing_result in existing_results:
                logger.debug(
                    f"Re-judging scenario '{existing_result.scenario_id}' "
                    f"variant '{existing_result.variant_id}'"
                )

                # Reconstruct scenario from stored data
                scenario = self._reconstruct_scenario(existing_result)

                # Execute judges on stored output
                new_result = await self.judge_executor.execute(
                    scenario=scenario,
                    subject_output=existing_result.processor_output,
                    variant_id=existing_result.variant_id,
                    subject_id=existing_result.subject_id,
                    metadata=existing_result.metadata,
                )

                # Merge results
                if preserve_existing:
                    merged_result = self._merge_results(
                        existing_result, new_result
                    )
                else:
                    merged_result = new_result

                rejudged_results.append(merged_result)

            logger.info(
                f"Re-judged {len(rejudged_results)} results with "
                f"{len(self.judge_executor.judges)} judges"
            )

            # Write to output file
            output_path = output_file or self.storage.results_file
            output_storage = ResultStorage(output_path)

            # Clear and write new results
            if output_path.exists():
                output_storage.clear()
            output_storage.append_batch(rejudged_results)

            span.set_attribute("rejudged.count", len(rejudged_results))
            return rejudged_results

    async def rejudge_by_scenario(
        self,
        scenario_id: str,
        preserve_existing: bool = True,
    ) -> List[EvaluationResult]:
        """
        Re-judge results for a specific scenario.

        Args:
            scenario_id: Scenario identifier to re-judge
            preserve_existing: If True, preserve existing judge evaluations

        Returns:
            List of updated EvaluationResults for the scenario
        """
        with self.tracer.start_as_current_span("rejudge.rejudge_by_scenario") as span:
            span.set_attribute("scenario.id", scenario_id)

            # Filter existing results
            existing_results = self.storage.filter_by_scenario(scenario_id)

            if not existing_results:
                logger.warning(f"No results found for scenario '{scenario_id}'")
                return []

            logger.info(
                f"Re-judging {len(existing_results)} results for scenario '{scenario_id}'"
            )

            # Re-judge each result
            rejudged_results: List[EvaluationResult] = []

            for existing_result in existing_results:
                scenario = self._reconstruct_scenario(existing_result)

                new_result = await self.judge_executor.execute(
                    scenario=scenario,
                    subject_output=existing_result.processor_output,
                    variant_id=existing_result.variant_id,
                    subject_id=existing_result.subject_id,
                    metadata=existing_result.metadata,
                )

                if preserve_existing:
                    merged_result = self._merge_results(
                        existing_result, new_result
                    )
                else:
                    merged_result = new_result

                rejudged_results.append(merged_result)

            span.set_attribute("rejudged.count", len(rejudged_results))
            return rejudged_results

    async def rejudge_by_variant(
        self,
        variant_id: str,
        preserve_existing: bool = True,
    ) -> List[EvaluationResult]:
        """
        Re-judge results for a specific variant.

        Args:
            variant_id: Variant identifier to re-judge
            preserve_existing: If True, preserve existing judge evaluations

        Returns:
            List of updated EvaluationResults for the variant
        """
        with self.tracer.start_as_current_span("rejudge.rejudge_by_variant") as span:
            span.set_attribute("variant.id", variant_id)

            # Filter existing results
            existing_results = self.storage.filter_by_variant(variant_id)

            if not existing_results:
                logger.warning(f"No results found for variant '{variant_id}'")
                return []

            logger.info(
                f"Re-judging {len(existing_results)} results for variant '{variant_id}'"
            )

            # Re-judge each result
            rejudged_results: List[EvaluationResult] = []

            for existing_result in existing_results:
                scenario = self._reconstruct_scenario(existing_result)

                new_result = await self.judge_executor.execute(
                    scenario=scenario,
                    subject_output=existing_result.processor_output,
                    variant_id=existing_result.variant_id,
                    subject_id=existing_result.subject_id,
                    metadata=existing_result.metadata,
                )

                if preserve_existing:
                    merged_result = self._merge_results(
                        existing_result, new_result
                    )
                else:
                    merged_result = new_result

                rejudged_results.append(merged_result)

            span.set_attribute("rejudged.count", len(rejudged_results))
            return rejudged_results

    def _reconstruct_scenario(self, result: EvaluationResult) -> Scenario:
        """
        Reconstruct Scenario object from stored result.

        Args:
            result: EvaluationResult to reconstruct scenario from

        Returns:
            Reconstructed Scenario
        """
        # Reconstruct scenario from stored data
        return Scenario(
            id=result.scenario_id,
            input=result.scenario_input,
            expected_behavior=result.expected_behavior,
            metadata=result.metadata,
        )

    def _merge_results(
        self,
        existing: EvaluationResult,
        new: EvaluationResult,
    ) -> EvaluationResult:
        """
        Merge existing and new judge results.

        Per Epic 4 Story 4.7: Old judge results are preserved and new
        results are added. If a judge with the same ID exists in both,
        the new result replaces the old one.

        Args:
            existing: Existing EvaluationResult with old judge evaluations
            new: New EvaluationResult with new judge evaluations

        Returns:
            Merged EvaluationResult with all judge evaluations
        """
        # Create map of existing judge evaluations by judge_id
        existing_judges = {j.judge_id: j for j in existing.judges}

        # Update with new judge evaluations (overwrites existing with same ID)
        for new_judge in new.judges:
            existing_judges[new_judge.judge_id] = new_judge

        # Create merged result
        merged_judges = list(existing_judges.values())

        return EvaluationResult(
            scenario_id=existing.scenario_id,
            variant_id=existing.variant_id,
            subject_id=existing.subject_id,
            scenario_input=existing.scenario_input,
            expected_behavior=existing.expected_behavior,
            processor_output=existing.processor_output,
            judges=merged_judges,
            timestamp=new.timestamp,  # Use new timestamp
            metadata=existing.metadata,
        )
