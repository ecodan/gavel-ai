"""Unit tests for TuneStep: prompts.toml roundtrip, score normalization, and
{{var}} placeholder preservation (with retry-then-abort)."""

import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import toml

from gavel_ai.core.contexts import IterationEvalContext, IterationRunContext
from gavel_ai.core.exceptions import ConfigError, ValidationError
from gavel_ai.core.steps.base import StepPhase
from gavel_ai.core.steps.tune_step import TuneStep
from gavel_ai.models.config import EvalConfig, ScenariosConfig, TestSubject, TuningConfig

pytestmark = pytest.mark.unit


def _make_eval_config(tuning: TuningConfig | None) -> EvalConfig:
    return EvalConfig(
        eval_type="oneshot",
        eval_name="test_eval",
        test_subject_type="local",
        test_subjects=[TestSubject(prompt_name="assistant", judges=[])],
        variants=["model-a"],
        scenarios=ScenariosConfig(source="file.local", name="scenarios.json"),
        workflow_type="autotune",
        tuning=tuning,
    )


def _make_tuning_config(**overrides) -> TuningConfig:
    base = {"max_rounds": 5, "tuning_agent_model": "claude-standard"}
    base.update(overrides)
    return TuningConfig(**base)


def _make_context(tmp_path: Path, eval_config: EvalConfig, evaluation_results, current_prompt: str):
    eval_dir = tmp_path / "test_eval"
    config_dir = eval_dir / "config"
    config_dir.mkdir(parents=True)

    base_eval_ctx = MagicMock()
    base_eval_ctx.eval_config.read.return_value = eval_config
    base_eval_ctx.agents.read.return_value = {"_models": {"claude-standard": {
        "model_provider": "anthropic",
        "model_family": "claude",
        "model_version": "claude-4-5-sonnet-latest",
        "model_parameters": {"temperature": 0.7},
        "provider_auth": {"api_key": "test-key"},
    }}}
    base_eval_ctx.eval_dir = eval_dir

    prompts_toml_path = tmp_path / "run-001" / "prompts.toml"
    prompts_toml_path.parent.mkdir(parents=True)
    toml.dump({"v1": {"prompt": current_prompt}}, open(prompts_toml_path, "w"))

    iter_eval_ctx = IterationEvalContext(base=base_eval_ctx, prompts_toml_path=prompts_toml_path, version="v1")

    run_dir = tmp_path / "run-001" / "iterations" / "iteration_1"
    run_dir.mkdir(parents=True)

    return IterationRunContext(
        eval_ctx=iter_eval_ctx,
        run_id="run-001",
        run_logger=logging.getLogger("test"),
        run_dir=run_dir,
        results_raw=MagicMock(),
        evaluation_results=evaluation_results,
    )


_JUDGE_FEEDBACK_RESULTS = [
    {
        "scenario_id": "s1",
        "variant_id": "model-a",
        "judges": [{"judge_id": "similarity", "score": 0.8, "reasoning": "good match"}],
    },
    {
        "scenario_id": "s2",
        "variant_id": "model-a",
        "judges": [{"judge_id": "similarity", "score": 0.6, "reasoning": "partial match"}],
    },
]


def _stub_tuning_agent(monkeypatch, *, side_effect) -> MagicMock:
    """Replace TuneStep's TuningAgent with a stub whose generate_improved_prompt yields side_effect."""
    agent = MagicMock()
    agent.generate_improved_prompt = AsyncMock(side_effect=side_effect)
    monkeypatch.setattr("gavel_ai.core.steps.tune_step.TuningAgent", lambda **kwargs: agent)
    return agent


class TestTuneStepPhase:
    def test_phase_is_tuning(self) -> None:
        assert TuneStep(logging.getLogger("test")).phase == StepPhase.TUNING


class TestTuneStepExecute:
    @pytest.mark.asyncio
    async def test_raises_config_error_when_tuning_not_configured(self, tmp_path: Path) -> None:
        eval_config = _make_eval_config(tuning=None)
        context = _make_context(tmp_path, eval_config, _JUDGE_FEEDBACK_RESULTS, "Answer {{input}}")

        with pytest.raises(ConfigError, match="EvalConfig.tuning"):
            await TuneStep(logging.getLogger("test")).execute(context)

    @pytest.mark.asyncio
    async def test_writes_next_version_with_normalized_avg_score(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        eval_config = _make_eval_config(tuning=_make_tuning_config())
        current_prompt = "Answer the question: {{input}}"
        context = _make_context(tmp_path, eval_config, _JUDGE_FEEDBACK_RESULTS, current_prompt)

        async def _generate(current_prompt, judge_feedback, iteration, eval_dir):
            return "Improved: " + current_prompt, {"tokens": 5}

        agent = _stub_tuning_agent(monkeypatch, side_effect=_generate)

        await TuneStep(logging.getLogger("test")).execute(context)

        prompts_data = toml.load(str(context.eval_ctx.prompts_toml_path))
        assert set(prompts_data.keys()) == {"v1", "v2"}
        assert prompts_data["v2"]["prompt"] == "Improved: " + current_prompt
        assert prompts_data["v2"]["iteration"] == 1
        # mean(0.8, 0.6) = 0.7 (native 0.0-1.0 scale, no rescaling)
        assert prompts_data["v2"]["avg_score"] == pytest.approx(0.7)

        agent.generate_improved_prompt.assert_awaited_once()
        _, kwargs = agent.generate_improved_prompt.call_args
        assert kwargs["current_prompt"] == current_prompt
        assert kwargs["iteration"] == 1
        assert {fb["scenario_id"] for fb in kwargs["judge_feedback"]} == {"s1", "s2"}

    @pytest.mark.asyncio
    async def test_retries_once_then_succeeds_on_placeholder_preservation(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        eval_config = _make_eval_config(tuning=_make_tuning_config())
        current_prompt = "Answer {{input}} given {{context}}"
        context = _make_context(tmp_path, eval_config, _JUDGE_FEEDBACK_RESULTS, current_prompt)

        agent = _stub_tuning_agent(
            monkeypatch,
            side_effect=[
                ("Dropped placeholder: {{input}}", {}),  # missing {{context}}
                ("Kept both: {{input}} {{context}}", {}),
            ],
        )

        await TuneStep(logging.getLogger("test")).execute(context)

        assert agent.generate_improved_prompt.await_count == 2
        prompts_data = toml.load(str(context.eval_ctx.prompts_toml_path))
        assert prompts_data["v2"]["prompt"] == "Kept both: {{input}} {{context}}"

    @pytest.mark.asyncio
    async def test_raises_validation_error_when_placeholder_missing_after_retry(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        eval_config = _make_eval_config(tuning=_make_tuning_config())
        current_prompt = "Answer {{input}} given {{context}}"
        context = _make_context(tmp_path, eval_config, _JUDGE_FEEDBACK_RESULTS, current_prompt)

        agent = _stub_tuning_agent(
            monkeypatch,
            side_effect=[
                ("Missing context: {{input}}", {}),
                ("Still missing: {{input}}", {}),
            ],
        )

        with pytest.raises(ValidationError, match="dropped required"):
            await TuneStep(logging.getLogger("test")).execute(context)

        assert agent.generate_improved_prompt.await_count == 2
        # Aborted before writing — prompts.toml still only has v1
        prompts_data = toml.load(str(context.eval_ctx.prompts_toml_path))
        assert set(prompts_data.keys()) == {"v1"}


class TestAggregateJudgeFeedback:
    def test_flattens_per_judge_entries(self) -> None:
        feedback = TuneStep._aggregate_judge_feedback(_JUDGE_FEEDBACK_RESULTS)
        assert feedback == [
            {"scenario_id": "s1", "judge_id": "similarity", "score": 0.8, "reasoning": "good match"},
            {"scenario_id": "s2", "judge_id": "similarity", "score": 0.6, "reasoning": "partial match"},
        ]

    def test_handles_empty_results(self) -> None:
        assert TuneStep._aggregate_judge_feedback([]) == []


class TestComputeAvgScore:
    def test_computes_mean_of_native_scale_scores(self) -> None:
        feedback = [{"score": 0.8}, {"score": 0.6}, {"score": 1.0}]
        assert TuneStep._compute_avg_score(feedback) == pytest.approx(0.8)

    def test_returns_zero_when_no_numeric_scores(self) -> None:
        assert TuneStep._compute_avg_score([{"score": None}, {"reasoning": "no score"}]) == 0.0
