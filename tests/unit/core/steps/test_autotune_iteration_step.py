"""Unit tests for AutotuneIterationStep: convergence criteria, score aggregation,
and the iterate -> score -> converge -> tune loop (with stubbed child steps)."""

import json
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional
from unittest.mock import MagicMock

import pytest

from gavel_ai.core.contexts import IterationRunContext
from gavel_ai.core.exceptions import ConfigError
from gavel_ai.core.steps.autotune_iteration_step import AutotuneIterationStep
from gavel_ai.core.steps.base import StepPhase
from gavel_ai.models.config import (
    EvalConfig,
    JudgeConfig,
    ScenariosConfig,
    TestSubject,
    TuningConfig,
)
from gavel_ai.models.runtime import OutputRecord

pytestmark = pytest.mark.unit


def _make_tuning_config(**overrides: Any) -> TuningConfig:
    base = {
        "max_rounds": 5,
        "convergence_threshold": 0.02,
        "target_score": None,
        "degradation_tolerance": 0.05,
        "tuning_agent_model": "claude-standard",
        "tuning_agent_temperature": 0.7,
    }
    base.update(overrides)
    return TuningConfig(**base)


def _make_eval_config(tuning: Optional[TuningConfig]) -> EvalConfig:
    return EvalConfig(
        eval_type="oneshot",
        eval_name="test_eval",
        test_subject_type="local",
        test_subjects=[
            TestSubject(
                prompt_name="assistant",
                judges=[JudgeConfig(name="similarity", type="deepeval.geval")],
            )
        ],
        variants=["model-a"],
        scenarios=ScenariosConfig(source="file.local", name="scenarios.json"),
        workflow_type="autotune",
        tuning=tuning,
    )


class TestCheckConvergence:
    """One scenario per criterion, verified in priority order."""

    def test_max_rounds_reached(self) -> None:
        config = _make_tuning_config(max_rounds=3)
        converged, reason = AutotuneIterationStep._check_convergence(
            iteration=3, current_score=0.5, previous_score=0.4, config=config
        )
        assert converged is True
        assert reason == "max_rounds_reached"

    def test_target_score_achieved(self) -> None:
        config = _make_tuning_config(target_score=0.9)
        converged, reason = AutotuneIterationStep._check_convergence(
            iteration=2, current_score=0.91, previous_score=0.83, config=config
        )
        assert converged is True
        assert reason == "target_score_achieved"

    def test_minimal_improvement(self) -> None:
        config = _make_tuning_config(convergence_threshold=0.02)
        converged, reason = AutotuneIterationStep._check_convergence(
            iteration=2, current_score=0.611, previous_score=0.6, config=config
        )
        assert converged is True
        assert reason == "minimal_improvement"

    def test_performance_degraded(self) -> None:
        config = _make_tuning_config(degradation_tolerance=0.05)
        converged, reason = AutotuneIterationStep._check_convergence(
            iteration=2, current_score=0.5, previous_score=0.6, config=config
        )
        assert converged is True
        assert reason == "performance_degraded"

    def test_not_converged_when_no_criterion_met(self) -> None:
        config = _make_tuning_config(max_rounds=5, convergence_threshold=0.02, degradation_tolerance=0.05)
        converged, reason = AutotuneIterationStep._check_convergence(
            iteration=1, current_score=0.6, previous_score=None, config=config
        )
        assert converged is False
        assert reason is None

    def test_max_rounds_takes_priority_over_target_score(self) -> None:
        """max_rounds_reached is checked first even if target_score is also satisfied."""
        config = _make_tuning_config(max_rounds=2, target_score=0.5)
        converged, reason = AutotuneIterationStep._check_convergence(
            iteration=2, current_score=0.9, previous_score=0.8, config=config
        )
        assert converged is True
        assert reason == "max_rounds_reached"


class TestScoreAggregationHelpers:
    _RESULTS = [
        {
            "scenario_id": "s1",
            "variant_id": "model-a",
            "judges": [
                {"judge_id": "similarity", "score": 0.8, "reasoning": "good"},
                {"judge_id": "accuracy", "score": 1, "reasoning": "pass"},
            ],
        },
        {
            "scenario_id": "s2",
            "variant_id": "model-a",
            "judges": [
                {"judge_id": "similarity", "score": 0.6, "reasoning": "ok"},
                {"judge_id": "accuracy", "score": 0, "reasoning": "fail"},
            ],
        },
    ]
    _JUDGE_TYPES = {"similarity": "deepeval.geval", "accuracy": "classifier"}

    def test_build_judge_type_map(self) -> None:
        eval_config = _make_eval_config(tuning=_make_tuning_config())
        eval_config.test_subjects = [
            TestSubject(
                prompt_name="assistant",
                judges=[
                    JudgeConfig(name="similarity", type="deepeval.geval"),
                    JudgeConfig(name="accuracy", type="classifier"),
                ],
            )
        ]
        assert AutotuneIterationStep._build_judge_type_map(eval_config) == {
            "similarity": "deepeval.geval",
            "accuracy": "classifier",
        }

    def test_compute_judge_scores_normalizes_per_judge_type(self) -> None:
        # similarity (LLM, native 0.0-1.0): mean(0.8, 0.6) = 0.7
        # accuracy (deterministic, pass-through): mean(1, 0) = 0.5
        scores = AutotuneIterationStep._compute_judge_scores(self._RESULTS, self._JUDGE_TYPES)
        assert scores == pytest.approx({"similarity": 0.7, "accuracy": 0.5})

    def test_compute_overall_score_means_all_normalized_individual_scores(self) -> None:
        # normalized values: [0.8, 1.0, 0.6, 0.0] -> mean = 0.6
        overall = AutotuneIterationStep._compute_overall_score(self._RESULTS, self._JUDGE_TYPES)
        assert overall == pytest.approx(0.6)

    def test_compute_overall_score_returns_zero_for_empty_results(self) -> None:
        assert AutotuneIterationStep._compute_overall_score([], {}) == 0.0

    def test_compute_judge_scores_returns_empty_dict_for_empty_results(self) -> None:
        assert AutotuneIterationStep._compute_judge_scores([], {}) == {}

    def test_unknown_judge_id_defaults_to_llm_normalization(self) -> None:
        results = [
            {
                "scenario_id": "s1",
                "variant_id": "model-a",
                "judges": [{"judge_id": "mystery", "score": 0.5, "reasoning": None}],
            }
        ]
        assert AutotuneIterationStep._compute_overall_score(results, {}) == pytest.approx(0.5)


class TestLoadPriorIterations:
    def test_no_prior_iterations_when_starting_at_one(self, tmp_path: Path) -> None:
        prior, previous_score = AutotuneIterationStep._load_prior_iterations(tmp_path / "iterations", 1)
        assert prior == []
        assert previous_score is None

    def test_reloads_completed_iteration_metadata(self, tmp_path: Path) -> None:
        from gavel_ai.models.config import IterationMetadata

        iterations_dir = tmp_path / "iterations"
        iter1_dir = iterations_dir / "iteration_1"
        iter1_dir.mkdir(parents=True)
        metadata = IterationMetadata(
            iteration=1, prompt_version="v1", score=0.65, improvement=0.0,
            judge_scores={"similarity": 0.65}, converged=False, convergence_reason=None,
        )
        (iter1_dir / "metadata.json").write_text(metadata.model_dump_json())

        prior, previous_score = AutotuneIterationStep._load_prior_iterations(iterations_dir, 2)
        assert len(prior) == 1
        assert prior[0].iteration == 1
        assert previous_score == pytest.approx(0.65)


# --- Loop-level tests with stubbed child steps -------------------------------------

OnExecute = Callable[[IterationRunContext], Awaitable[bool]]


class _StubStep:
    """Replaces a real child step: records calls and runs a caller-supplied effect."""

    def __init__(self, phase: StepPhase, on_execute: OnExecute):
        self.phase = phase
        self._on_execute = on_execute
        self.call_count = 0

    async def safe_execute(self, context: IterationRunContext, error_policy: Any = None) -> bool:
        self.call_count += 1
        return await self._on_execute(context)


def _record(scenario_id: str, score_iteration: int) -> OutputRecord:
    return OutputRecord(
        test_subject="assistant",
        variant_id="model-a",
        scenario_id=scenario_id,
        processor_output=f"output for {scenario_id} @ iter {score_iteration}",
        timing_ms=10,
        tokens_prompt=5,
        tokens_completion=5,
        timestamp="2026-06-07T00:00:00Z",
    )


def _make_processor_effect() -> OnExecute:
    async def _effect(context: IterationRunContext) -> bool:
        records = [_record("s1", 1)]
        context.processor_results = records
        context.test_subject = "assistant"
        context.model_variant = "model-a"
        for record in records:
            context.results_raw.append(record)
        return True

    return _effect


def _make_judge_effect(scores_by_iteration: Dict[int, float]) -> OnExecute:
    """scores_by_iteration maps iteration number (1-based call order) -> raw 0.0-1.0 score."""
    state = {"call": 0}

    async def _effect(context: IterationRunContext) -> bool:
        state["call"] += 1
        score = scores_by_iteration[state["call"]]
        context.evaluation_results = [
            {
                "scenario_id": "s1",
                "variant_id": "model-a",
                "judges": [{"judge_id": "similarity", "score": score, "reasoning": "stub"}],
            }
        ]
        context.deterministic_metrics = {}
        return True

    return _effect


def _stub_child_steps(
    monkeypatch: pytest.MonkeyPatch, *, judge_scores_by_call: Dict[int, float]
) -> Dict[str, _StubStep]:
    processor = _StubStep(StepPhase.SCENARIO_PROCESSING, _make_processor_effect())
    judge = _StubStep(StepPhase.JUDGING, _make_judge_effect(judge_scores_by_call))

    async def _tune_effect(context: IterationRunContext) -> bool:
        return True

    tune = _StubStep(StepPhase.TUNING, _tune_effect)

    monkeypatch.setattr(
        "gavel_ai.core.steps.autotune_iteration_step.ScenarioProcessorStep", lambda logger: processor
    )
    monkeypatch.setattr(
        "gavel_ai.core.steps.autotune_iteration_step.JudgeRunnerStep", lambda logger: judge
    )
    monkeypatch.setattr("gavel_ai.core.steps.autotune_iteration_step.TuneStep", lambda logger: tune)

    return {"processor": processor, "judge": judge, "tune": tune}


def _make_run_context(tmp_path: Path, eval_config: EvalConfig) -> MagicMock:
    run_dir = tmp_path / "run-001"
    run_dir.mkdir(parents=True)

    context = MagicMock()
    context.eval_context.eval_config.read.return_value = eval_config
    context.eval_context.eval_name = "test_eval"
    context.run_dir = run_dir
    context.run_id = "run-001"
    context.run_logger = logging.getLogger("test")
    return context


class TestAutotuneIterationStepExecute:
    @pytest.mark.asyncio
    async def test_raises_config_error_when_tuning_not_configured(self, tmp_path: Path) -> None:
        eval_config = _make_eval_config(tuning=None)
        context = _make_run_context(tmp_path, eval_config)

        with pytest.raises(ConfigError, match="EvalConfig.tuning"):
            await AutotuneIterationStep(logging.getLogger("test")).execute(context)

    @pytest.mark.asyncio
    async def test_loop_converges_on_minimal_improvement_and_skips_final_tune(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # iter 1: raw score 0.6 (no previous score, not converged)
        # iter 2: raw score 0.6 again -> |0.6 - 0.6| = 0.0 < 0.05 => minimal_improvement
        eval_config = _make_eval_config(
            tuning=_make_tuning_config(max_rounds=5, convergence_threshold=0.05, degradation_tolerance=0.05)
        )
        context = _make_run_context(tmp_path, eval_config)
        stubs = _stub_child_steps(monkeypatch, judge_scores_by_call={1: 0.6, 2: 0.6})

        await AutotuneIterationStep(logging.getLogger("test")).execute(context)

        assert stubs["processor"].call_count == 2
        assert stubs["judge"].call_count == 2
        # TuneStep runs after iteration 1 (not converged), but not after iteration 2 (converged)
        assert stubs["tune"].call_count == 1

        run_dir = context.run_dir
        iter1_meta = json.loads((run_dir / "iterations" / "iteration_1" / "metadata.json").read_text())
        iter2_meta = json.loads((run_dir / "iterations" / "iteration_2" / "metadata.json").read_text())

        assert iter1_meta["converged"] is False
        assert iter1_meta["convergence_reason"] is None
        assert iter1_meta["score"] == pytest.approx(0.6)

        assert iter2_meta["converged"] is True
        assert iter2_meta["convergence_reason"] == "minimal_improvement"
        assert iter2_meta["score"] == pytest.approx(0.6)
        assert iter2_meta["improvement"] == pytest.approx(0.0)

        # Per-iteration artifacts persisted
        assert (run_dir / "iterations" / "iteration_1" / "output_raw.jsonl").exists()
        assert (run_dir / "iterations" / "iteration_1" / "output_judged.jsonl").exists()
        assert (run_dir / "iterations" / "iteration_2" / "output_raw.jsonl").exists()
        assert (run_dir / "iterations" / "iteration_2" / "output_judged.jsonl").exists()

        judged_lines = (
            (run_dir / "iterations" / "iteration_1" / "output_judged.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        assert len(judged_lines) == 1
        judged_entry = json.loads(judged_lines[0])
        assert judged_entry["scenario_id"] == "s1"
        assert judged_entry["judges"][0]["judge_id"] == "similarity"

        # run_summary.json reflects both iterations
        summary = json.loads((run_dir / "run_summary.json").read_text())
        assert summary["total_iterations"] == 2
        assert summary["best_iteration"] in (1, 2)
        assert summary["final_score"] == pytest.approx(0.6)
        assert summary["converged"] is True
        assert summary["convergence_reason"] == "minimal_improvement"

    @pytest.mark.asyncio
    async def test_loop_stops_at_max_rounds_when_no_other_criterion_met(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        eval_config = _make_eval_config(
            tuning=_make_tuning_config(
                max_rounds=2, convergence_threshold=0.0, degradation_tolerance=1.0, target_score=None
            )
        )
        context = _make_run_context(tmp_path, eval_config)
        # Large jump (0.3 -> 0.9) avoids minimal_improvement/performance_degraded triggering early
        stubs = _stub_child_steps(monkeypatch, judge_scores_by_call={1: 0.3, 2: 0.9})

        await AutotuneIterationStep(logging.getLogger("test")).execute(context)

        assert stubs["processor"].call_count == 2
        assert stubs["tune"].call_count == 1

        run_dir = context.run_dir
        iter2_meta = json.loads((run_dir / "iterations" / "iteration_2" / "metadata.json").read_text())
        assert iter2_meta["converged"] is True
        assert iter2_meta["convergence_reason"] == "max_rounds_reached"

        summary = json.loads((run_dir / "run_summary.json").read_text())
        assert summary["best_iteration"] == 2
        assert summary["best_score"] == pytest.approx(0.9)
