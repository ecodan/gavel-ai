"""AutotuneIterationStep: runs the prompt-tuning loop to convergence.

Each iteration creates a per-iteration IterationRunContext rooted at
iterations/iteration_N/, runs ScenarioProcessorStep + JudgeRunnerStep against
the current prompt version, persists output_raw.jsonl/output_judged.jsonl and
metadata.json, checks convergence, and — if not yet converged — runs TuneStep
to generate the next prompt version. On exit, writes run_summary.json.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from gavel_ai.core.adapters.backends import LocalStorageBackend
from gavel_ai.core.adapters.data_sources import RecordDataSource, StructDataSource
from gavel_ai.core.autotune.scoring import normalize_score
from gavel_ai.core.contexts import IterationEvalContext, IterationRunContext, LocalRunContext
from gavel_ai.core.exceptions import ConfigError, ProcessorError
from gavel_ai.core.steps.base import CompositeStep, StepPhase
from gavel_ai.core.steps.judge_runner import JudgeRunnerStep
from gavel_ai.core.steps.scenario_processor import ScenarioProcessorStep
from gavel_ai.core.steps.tune_step import TuneStep
from gavel_ai.models.config import AutotuneRunSummary, EvalConfig, IterationMetadata, TuningConfig
from gavel_ai.models.runtime import OutputRecord


class AutotuneIterationStep(CompositeStep):
    """Drives the iterate → score → check-convergence → tune loop for autotune runs."""

    def __init__(self, logger: logging.Logger, start_iteration: int = 1):
        super().__init__(
            child_steps=[ScenarioProcessorStep(logger), JudgeRunnerStep(logger), TuneStep(logger)],
            logger=logger,
        )
        self._start_iteration = start_iteration

    @property
    def phase(self) -> StepPhase:
        return StepPhase.AUTOTUNE_ITERATION

    async def execute(self, context: LocalRunContext) -> None:
        """
        Raises:
            ConfigError: If EvalConfig.tuning is not configured.
            ProcessorError: If ScenarioProcessorStep, JudgeRunnerStep, or TuneStep
                fails without raising RunPolicyError (i.e. a non-halting terminal
                error per ErrorPolicy) — aborts the run so partial iteration data
                is not silently treated as complete.

        Note: RunPolicyError raised by any child step's safe_execute() is not
        caught here — it propagates to AutotuneWorkflow per FR-7.2.
        """
        eval_config = context.eval_context.eval_config.read()
        tuning_config: Optional[TuningConfig] = eval_config.tuning
        if tuning_config is None:
            raise ConfigError(
                "AutotuneIterationStep requires EvalConfig.tuning to be set for workflow_type='autotune'"
            )

        error_policy = eval_config.error_policy
        processor_step, judge_step, tune_step = self.child_steps

        prompts_toml_path = context.run_dir / "prompts.toml"
        iterations_dir = context.run_dir / "iterations"
        storage = LocalStorageBackend(context.run_dir)
        judge_type_by_id = self._build_judge_type_map(eval_config)

        iterations_metadata, previous_score = self._load_prior_iterations(iterations_dir, self._start_iteration)

        for iteration in range(self._start_iteration, tuning_config.max_rounds + 1):
            version = f"v{iteration}"
            iteration_dir = iterations_dir / f"iteration_{iteration}"
            iteration_dir.mkdir(parents=True, exist_ok=True)

            iter_eval_ctx = IterationEvalContext(
                base=context.eval_context, prompts_toml_path=prompts_toml_path, version=version
            )
            output_raw = RecordDataSource(
                storage, f"iterations/iteration_{iteration}/output_raw.jsonl", schema=OutputRecord
            )
            iteration_ctx = IterationRunContext(
                eval_ctx=iter_eval_ctx,
                run_id=context.run_id,
                run_logger=context.run_logger,
                run_dir=iteration_dir,
                results_raw=output_raw,
            )

            with self.tracer.start_as_current_span("autotune.iteration") as span:
                span.set_attribute("autotune.iteration", iteration)
                span.set_attribute("autotune.prompt_version", version)

                for step in (processor_step, judge_step):
                    ok = await step.safe_execute(iteration_ctx, error_policy)
                    if not ok:
                        raise ProcessorError(
                            f"Autotune iteration {iteration}: {step.phase.value} failed"
                        ) from iteration_ctx.last_step_error

                self._write_output_judged(storage, iteration, iteration_ctx)

                judge_scores = self._compute_judge_scores(
                    iteration_ctx.evaluation_results or [], judge_type_by_id
                )
                current_score = self._compute_overall_score(
                    iteration_ctx.evaluation_results or [], judge_type_by_id
                )
                improvement = 0.0 if previous_score is None else current_score - previous_score
                converged, reason = self._check_convergence(
                    iteration, current_score, previous_score, tuning_config
                )

                metadata = IterationMetadata(
                    iteration=iteration,
                    prompt_version=version,
                    score=current_score,
                    improvement=improvement,
                    judge_scores=judge_scores,
                    converged=converged,
                    convergence_reason=reason,
                )
                self._write_metadata(storage, iteration, metadata)
                iterations_metadata.append(metadata)

                span.set_attribute("autotune.score", current_score)
                span.set_attribute("autotune.converged", converged)

                if converged:
                    self.logger.info(
                        f"Autotune converged at iteration {iteration}: {reason} (score={current_score:.3f})"
                    )
                    break

                ok = await tune_step.safe_execute(iteration_ctx, error_policy)
                if not ok:
                    raise ProcessorError(
                        f"Autotune iteration {iteration}: tuning failed"
                    ) from iteration_ctx.last_step_error

                previous_score = current_score

        self._write_run_summary(context, iterations_metadata)

    @staticmethod
    def _build_judge_type_map(eval_config: EvalConfig) -> Dict[str, str]:
        """Map judge name -> judge type (e.g. {"similarity": "deepeval.geval"})."""
        judge_types: Dict[str, str] = {}
        for subject in eval_config.test_subjects or []:
            for judge in subject.judges or []:
                judge_types[judge.name] = judge.type
        return judge_types

    @staticmethod
    def _load_prior_iterations(
        iterations_dir: Path, start_iteration: int
    ) -> Tuple[List[IterationMetadata], Optional[float]]:
        """Reload metadata.json for already-completed iterations (resume support)."""
        prior: List[IterationMetadata] = []
        previous_score: Optional[float] = None
        for n in range(1, start_iteration):
            meta_path = iterations_dir / f"iteration_{n}" / "metadata.json"
            if not meta_path.exists():
                continue
            metadata = IterationMetadata(**json.loads(meta_path.read_text(encoding="utf-8")))
            prior.append(metadata)
            previous_score = metadata.score
        return prior, previous_score

    @staticmethod
    def _flatten_judge_scores(
        evaluation_results: List[Dict[str, Any]], judge_type_by_id: Dict[str, str]
    ) -> List[Tuple[str, float]]:
        """Flatten evaluation_results into (judge_id, normalized_score) pairs."""
        flat: List[Tuple[str, float]] = []
        for entry in evaluation_results:
            for judge_eval in entry.get("judges", []):
                judge_id = judge_eval.get("judge_id")
                score = judge_eval.get("score")
                if judge_id is None or not isinstance(score, (int, float)):
                    continue
                judge_type = judge_type_by_id.get(judge_id, "deepeval.geval")
                flat.append((judge_id, normalize_score(score, judge_type)))
        return flat

    @classmethod
    def _compute_judge_scores(
        cls, evaluation_results: List[Dict[str, Any]], judge_type_by_id: Dict[str, str]
    ) -> Dict[str, float]:
        """Per-judge mean normalized score: {judge_id: mean_score}."""
        totals: Dict[str, List[float]] = {}
        for judge_id, normalized in cls._flatten_judge_scores(evaluation_results, judge_type_by_id):
            totals.setdefault(judge_id, []).append(normalized)
        return {judge_id: sum(scores) / len(scores) for judge_id, scores in totals.items()}

    @classmethod
    def _compute_overall_score(
        cls, evaluation_results: List[Dict[str, Any]], judge_type_by_id: Dict[str, str]
    ) -> float:
        """Mean normalized score across all scenarios and all LLM judges (0.0-1.0)."""
        flat = cls._flatten_judge_scores(evaluation_results, judge_type_by_id)
        if not flat:
            return 0.0
        return sum(normalized for _, normalized in flat) / len(flat)

    @staticmethod
    def _check_convergence(
        iteration: int,
        current_score: float,
        previous_score: Optional[float],
        config: TuningConfig,
    ) -> Tuple[bool, Optional[str]]:
        """Four convergence criteria, checked in order.

        1. max_rounds_reached — the hard upper bound on iterations.
        2. target_score_achieved — current_score has reached the configured target.
        3. minimal_improvement — score barely moved since the previous iteration.
        4. performance_degraded — score dropped beyond the allowed tolerance.
        """
        if iteration >= config.max_rounds:
            return True, "max_rounds_reached"

        if config.target_score is not None and current_score >= config.target_score:
            return True, "target_score_achieved"

        if previous_score is not None:
            if abs(current_score - previous_score) < config.convergence_threshold:
                return True, "minimal_improvement"
            if previous_score - current_score > config.degradation_tolerance:
                return True, "performance_degraded"

        return False, None

    @staticmethod
    def _write_output_judged(
        storage: LocalStorageBackend, iteration: int, iteration_ctx: IterationRunContext
    ) -> None:
        """Join processor_results with evaluation_results and persist to output_judged.jsonl."""
        output_judged = RecordDataSource(
            storage, f"iterations/iteration_{iteration}/output_judged.jsonl", schema=None
        )
        evaluation_results = iteration_ctx.evaluation_results or []
        eval_by_key = {(e["scenario_id"], e["variant_id"]): e for e in evaluation_results}

        for record in iteration_ctx.processor_results:
            eval_entry = eval_by_key.get((record.scenario_id, record.variant_id), {})
            entry = {
                **record.model_dump(exclude={"metadata"}),
                "judges": eval_entry.get("judges", []),
            }
            output_judged.append(entry)

    @staticmethod
    def _write_metadata(storage: LocalStorageBackend, iteration: int, metadata: IterationMetadata) -> None:
        source = StructDataSource(storage, f"iterations/iteration_{iteration}/metadata.json")
        source.write(metadata)

    @staticmethod
    def _write_run_summary(context: LocalRunContext, iterations: List[IterationMetadata]) -> None:
        if not iterations:
            return

        best = max(iterations, key=lambda m: m.score)
        final = iterations[-1]
        summary = AutotuneRunSummary(
            eval_name=context.eval_context.eval_name,
            run_id=context.run_id,
            total_iterations=len(iterations),
            best_iteration=best.iteration,
            best_score=best.score,
            final_score=final.score,
            converged=final.converged,
            convergence_reason=final.convergence_reason,
            iterations=iterations,
        )
        source = StructDataSource(LocalStorageBackend(context.run_dir), "run_summary.json")
        source.write(summary)


__all__ = ["AutotuneIterationStep"]
