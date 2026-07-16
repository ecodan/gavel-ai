"""TuneStep: generates and persists the next prompt version from judge feedback.

Reads the current iteration's judge results, calls TuningAgent for an improved
prompt, validates that all `{{var}}` placeholders survive the rewrite (with one
retry on failure), and appends the new version to the run-local prompts.toml.
"""

import logging
import re
from typing import Any, Dict, List

import toml

from gavel_ai.core.autotune.tuning_agent import TuningAgent
from gavel_ai.core.contexts import IterationRunContext
from gavel_ai.core.exceptions import ConfigError, ValidationError
from gavel_ai.core.steps.base import Step, StepPhase

_PLACEHOLDER_RE = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}")


class TuneStep(Step):
    """Generates prompt vN+1 from judge feedback on vN and appends it to prompts.toml."""

    def __init__(self, logger: logging.Logger):
        super().__init__(logger)

    @property
    def phase(self) -> StepPhase:
        return StepPhase.TUNING

    async def execute(self, context: IterationRunContext) -> None:
        """
        Raises:
            ConfigError: If EvalConfig.tuning is not configured.
            ValidationError: If the generated prompt drops `{{var}}` placeholders
                after one retry — aborts the iteration.

        Note: RunPolicyError from TuningAgent's ProviderFactory call is not caught
        here; it propagates to AutotuneIterationStep / AutotuneWorkflow (FR-7.2).
        """
        eval_config = context.eval_context.eval_config.read()
        tuning_config = eval_config.tuning
        if tuning_config is None:
            raise ConfigError(
                "TuneStep requires EvalConfig.tuning to be set for workflow_type='autotune'"
            )

        prompts_toml_path = context.eval_ctx.prompts_toml_path
        current_version = context.eval_ctx.version
        current_iteration = int(current_version.lstrip("v"))

        prompts_data: Dict[str, Any] = toml.load(str(prompts_toml_path))
        current_prompt: str = prompts_data[current_version]["prompt"]

        judge_feedback = self._aggregate_judge_feedback(context.evaluation_results or [])
        avg_score = self._compute_avg_score(judge_feedback)

        agents_config = context.eval_context.agents.read()
        eval_dir = context.eval_context.eval_dir
        tuning_agent = TuningAgent(
            model_id=tuning_config.tuning_agent_model,
            agents_config=agents_config,
            temperature=tuning_config.tuning_agent_temperature,
        )

        next_version = f"v{current_iteration + 1}"
        improved_prompt = await self._generate_with_retry(
            tuning_agent, current_prompt, judge_feedback, current_iteration, eval_dir, next_version
        )

        prompts_data[next_version] = {
            "prompt": improved_prompt,
            "iteration": current_iteration,
            "avg_score": avg_score,
        }
        with open(prompts_toml_path, "w", encoding="utf-8") as f:
            toml.dump(prompts_data, f)

        self.logger.info(
            f"TuneStep: wrote prompt {next_version} (avg_score={avg_score:.3f}) to {prompts_toml_path}"
        )

    @staticmethod
    def _aggregate_judge_feedback(evaluation_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Flatten output_judged.jsonl entries into one feedback dict per (scenario, judge)."""
        feedback: List[Dict[str, Any]] = []
        for entry in evaluation_results:
            scenario_id = entry.get("scenario_id")
            for judge_eval in entry.get("judges", []):
                feedback.append(
                    {
                        "scenario_id": scenario_id,
                        "judge_id": judge_eval.get("judge_id"),
                        "score": judge_eval.get("score"),
                        "reasoning": judge_eval.get("reasoning"),
                    }
                )
        return feedback

    @staticmethod
    def _compute_avg_score(judge_feedback: List[Dict[str, Any]]) -> float:
        """Mean of judge_feedback scores, already on the native 0.0-1.0 LLM-judge scale.

        output_judged.jsonl (and thus context.evaluation_results) only ever contains
        LLM judge results — deterministic classifier/regression results are tracked
        separately in context.deterministic_metrics.
        """
        scores = [fb["score"] for fb in judge_feedback if isinstance(fb.get("score"), (int, float))]
        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    async def _generate_with_retry(
        self,
        tuning_agent: TuningAgent,
        current_prompt: str,
        judge_feedback: List[Dict[str, Any]],
        iteration: int,
        eval_dir: Any,
        next_version: str,
    ) -> str:
        """Call TuningAgent; retry once if `{{var}}` placeholders are dropped, then abort."""
        required_placeholders = set(_PLACEHOLDER_RE.findall(current_prompt))

        for attempt in range(2):
            improved_prompt, _metadata = await tuning_agent.generate_improved_prompt(
                current_prompt=current_prompt,
                judge_feedback=judge_feedback,
                iteration=iteration,
                eval_dir=eval_dir,
            )
            missing = required_placeholders - set(_PLACEHOLDER_RE.findall(improved_prompt))
            if not missing:
                return improved_prompt
            self.logger.warning(
                f"TuneStep: generated prompt for {next_version} dropped placeholder(s) "
                f"{sorted(missing)} (attempt {attempt + 1}/2)"
            )

        raise ValidationError(
            f"TuneStep: generated prompt for {next_version} dropped required {{var}} "
            f"placeholder(s) {sorted(missing)} after retry — aborting iteration"
        )
