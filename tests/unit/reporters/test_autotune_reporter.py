"""Unit tests for AutotuneReporter: _build_context() structure and template rendering."""

from pathlib import Path

import pytest

from gavel_ai.models.config import AutotuneRunSummary, IterationMetadata
from gavel_ai.models.runtime import ReporterConfig
from gavel_ai.reporters.autotune_reporter import AutotuneReporter, AutotuneRunData

pytestmark = pytest.mark.unit

_TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "src" / "gavel_ai" / "reporters" / "templates"


def _make_run_summary() -> AutotuneRunSummary:
    iterations = [
        IterationMetadata(
            iteration=1, prompt_version="v1", score=0.6, improvement=0.0,
            judge_scores={"similarity": 0.6, "accuracy": 0.5},
            converged=False, convergence_reason=None,
        ),
        IterationMetadata(
            iteration=2, prompt_version="v2", score=0.85, improvement=0.25,
            judge_scores={"similarity": 0.9, "accuracy": 0.8},
            converged=False, convergence_reason=None,
        ),
        IterationMetadata(
            iteration=3, prompt_version="v3", score=0.86, improvement=0.01,
            judge_scores={"similarity": 0.92, "accuracy": 0.8},
            converged=True, convergence_reason="minimal_improvement",
        ),
    ]
    return AutotuneRunSummary(
        eval_name="test_eval",
        run_id="run-001",
        total_iterations=3,
        best_iteration=3,
        best_score=0.86,
        final_score=0.86,
        converged=True,
        convergence_reason="minimal_improvement",
        iterations=iterations,
    )


def _make_reporter() -> AutotuneReporter:
    config = ReporterConfig(template_path=str(_TEMPLATES_DIR), output_format="html")
    return AutotuneReporter(config)


class TestBuildContext:
    def test_run_level_fields(self) -> None:
        run_summary = _make_run_summary()
        run = AutotuneRunData(
            run_summary=run_summary,
            best_prompt_text="Improved: Answer {{input}}",
            prompts_toml_path="runs/run-001/prompts.toml",
        )
        context = _make_reporter()._build_context(run)

        assert context["eval_name"] == "test_eval"
        assert context["run_id"] == "run-001"
        assert context["total_iterations"] == 3
        assert context["best_iteration"] == 3
        assert context["best_score"] == pytest.approx(0.86)
        assert context["final_score"] == pytest.approx(0.86)
        assert context["converged"] is True
        assert context["convergence_reason"] == "minimal_improvement"

    def test_judge_names_collected_in_first_seen_order_deduplicated(self) -> None:
        run = AutotuneRunData(
            run_summary=_make_run_summary(), best_prompt_text="x", prompts_toml_path="p"
        )
        context = _make_reporter()._build_context(run)
        assert context["judge_names"] == ["similarity", "accuracy"]

    def test_iteration_rows_carry_per_judge_breakdown_and_flags(self) -> None:
        run = AutotuneRunData(
            run_summary=_make_run_summary(), best_prompt_text="x", prompts_toml_path="p"
        )
        rows = _make_reporter()._build_context(run)["iterations"]

        assert len(rows) == 3
        assert [row["iteration"] for row in rows] == [1, 2, 3]

        row1, row2, row3 = rows
        assert row1["judge_scores"] == {"similarity": pytest.approx(0.6), "accuracy": pytest.approx(0.5)}
        assert row1["is_best"] is False
        assert row1["is_final"] is False

        assert row3["is_best"] is True
        assert row3["is_final"] is True
        assert row3["convergence_reason"] == "minimal_improvement"

        assert row2["improvement"] == pytest.approx(0.25)

    def test_iteration_rows_fill_missing_judge_with_none(self) -> None:
        iterations = [
            IterationMetadata(
                iteration=1, prompt_version="v1", score=0.5, improvement=0.0,
                judge_scores={"similarity": 0.5}, converged=False, convergence_reason=None,
            ),
            IterationMetadata(
                iteration=2, prompt_version="v2", score=0.6, improvement=0.1,
                judge_scores={"similarity": 0.6, "new_judge": 0.4},
                converged=True, convergence_reason="max_rounds_reached",
            ),
        ]
        run_summary = AutotuneRunSummary(
            eval_name="test_eval", run_id="run-002", total_iterations=2, best_iteration=2,
            best_score=0.6, final_score=0.6, converged=True, convergence_reason="max_rounds_reached",
            iterations=iterations,
        )
        run = AutotuneRunData(run_summary=run_summary, best_prompt_text="x", prompts_toml_path="p")
        rows = _make_reporter()._build_context(run)["iterations"]

        assert rows[0]["judge_scores"] == {"similarity": pytest.approx(0.5), "new_judge": None}
        assert rows[1]["judge_scores"] == {"similarity": pytest.approx(0.6), "new_judge": pytest.approx(0.4)}

    def test_best_prompt_section(self) -> None:
        run = AutotuneRunData(
            run_summary=_make_run_summary(),
            best_prompt_text="Improved: Answer {{input}} with {{context}}",
            prompts_toml_path="runs/run-001/prompts.toml",
        )
        best_prompt = _make_reporter()._build_context(run)["best_prompt"]

        assert best_prompt["iteration"] == 3
        assert best_prompt["version"] == "v3"
        assert best_prompt["text"] == "Improved: Answer {{input}} with {{context}}"
        assert best_prompt["file_path"] == "runs/run-001/prompts.toml"


class TestGenerate:
    @pytest.mark.asyncio
    async def test_renders_autotune_html_with_key_content(self) -> None:
        run = AutotuneRunData(
            run_summary=_make_run_summary(),
            best_prompt_text="Improved: Answer {{input}}",
            prompts_toml_path="runs/run-001/prompts.toml",
        )
        html = await _make_reporter().generate(run, "autotune.html")

        assert "test_eval" in html
        assert "run-001" in html
        assert "minimal_improvement" in html
        assert "Improved: Answer {{input}}" in html
        assert "runs/run-001/prompts.toml" in html
        assert "similarity" in html and "accuracy" in html
