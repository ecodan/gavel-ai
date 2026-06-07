"""Autotune report generator: renders the score-progression / best-prompt report.

Builds a Jinja2 context from an AutotuneRunData bundle (run summary + best
prompt text/path) so the template can render a per-iteration score table with
per-judge sub-columns, a per-judge detail breakdown, and a copyable best-prompt
section with promotion instructions.
"""

from dataclasses import dataclass
from typing import Any, Dict, List

from gavel_ai.models.config import AutotuneRunSummary, IterationMetadata
from gavel_ai.models.runtime import ReporterConfig
from gavel_ai.reporters.jinja_reporter import Jinja2Reporter


@dataclass
class AutotuneRunData:
    """Bundles the persisted run summary with prompt-version material the template needs."""

    run_summary: AutotuneRunSummary
    best_prompt_text: str
    prompts_toml_path: str


class AutotuneReporter(Jinja2Reporter):
    """Renders `autotune.html` from an AutotuneRunData bundle."""

    def __init__(self, config: ReporterConfig):
        super().__init__(config)

    def _build_context(self, run: AutotuneRunData) -> Dict[str, Any]:
        run_summary = run.run_summary
        judge_names = self._collect_judge_names(run_summary.iterations)

        return {
            "title": f"Autotune Report — {run_summary.eval_name}",
            "eval_name": run_summary.eval_name,
            "run_id": run_summary.run_id,
            "total_iterations": run_summary.total_iterations,
            "best_iteration": run_summary.best_iteration,
            "best_score": run_summary.best_score,
            "final_score": run_summary.final_score,
            "converged": run_summary.converged,
            "convergence_reason": run_summary.convergence_reason,
            "judge_names": judge_names,
            "iterations": self._build_iteration_rows(run_summary, judge_names),
            "best_prompt": {
                "iteration": run_summary.best_iteration,
                "version": f"v{run_summary.best_iteration}",
                "text": run.best_prompt_text,
                "file_path": run.prompts_toml_path,
            },
        }

    @staticmethod
    def _collect_judge_names(iterations: List[IterationMetadata]) -> List[str]:
        """Stable, de-duplicated judge name list across all iterations (for sub-columns)."""
        seen: Dict[str, None] = {}
        for iteration in iterations:
            for judge_name in iteration.judge_scores:
                seen.setdefault(judge_name, None)
        return list(seen.keys())

    @staticmethod
    def _build_iteration_rows(
        run_summary: AutotuneRunSummary, judge_names: List[str]
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        last_index = len(run_summary.iterations) - 1
        for index, iteration in enumerate(run_summary.iterations):
            rows.append(
                {
                    "iteration": iteration.iteration,
                    "prompt_version": iteration.prompt_version,
                    "score": iteration.score,
                    "improvement": iteration.improvement,
                    "convergence_reason": iteration.convergence_reason,
                    "judge_scores": {name: iteration.judge_scores.get(name) for name in judge_names},
                    "is_best": iteration.iteration == run_summary.best_iteration,
                    "is_final": index == last_index,
                }
            )
        return rows


__all__ = ["AutotuneReporter", "AutotuneRunData"]
