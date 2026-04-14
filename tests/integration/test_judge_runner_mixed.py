"""
Integration test: JudgeRunnerStep with mixed LLM + deterministic judges.

Confirms:
- context.deterministic_metrics is populated correctly for classifier judges
- context.evaluation_results is populated for LLM judges
- Both judge types run independently on the same processor_results
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, patch

import pytest

from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext
from gavel_ai.core.steps.judge_runner import JudgeRunnerStep
from gavel_ai.models.runtime import EvaluationResult, JudgeEvaluation, OutputRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_eval_dir(tmp_path: Path, eval_name: str = "mixed-judge-eval") -> Path:
    """
    Create a minimal eval directory with:
    - One classifier judge (deterministic, no LLM)
    - One deepeval.geval judge (LLM, will be mocked)
    - Three scenarios with prediction labels embedded in input
    """
    config_dir = tmp_path / eval_name / "config"
    data_dir = tmp_path / eval_name / "data"
    config_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)

    eval_config = {
        "eval_name": eval_name,
        "eval_type": "oneshot",
        "test_subject_type": "local",
        "test_subjects": [
            {
                "prompt_name": "default",
                "judges": [
                    # Deterministic: classifier
                    {
                        "name": "label_acc",
                        "type": "classifier",
                        "config": {
                            "prediction_field": "label",
                            "actual_field": "expected",
                            "report_metric": "accuracy",
                        },
                    },
                    # LLM judge (will be mocked)
                    {
                        "name": "quality",
                        "type": "deepeval.geval",
                        "config": {
                            "criteria": "Is the label correct?",
                            "evaluation_steps": ["Check if label matches expected."],
                            "threshold": 0.5,
                            "model": "claude-test",
                        },
                    },
                ],
            }
        ],
        "variants": ["claude-test"],
        "scenarios": {"source": "file.local", "name": "scenarios.json"},
    }
    (config_dir / "eval_config.json").write_text(json.dumps(eval_config))

    agents = {
        "_models": {
            "claude-test": {
                "model_provider": "anthropic",
                "model_family": "claude",
                "model_version": "claude-haiku-4-5-20251001",
                "model_parameters": {"temperature": 0.0},
                "provider_auth": {"api_key": "sk-test"},
            }
        }
    }
    (config_dir / "agents.json").write_text(json.dumps(agents))

    # Scenarios: expected label stored in input dict so _resolve_actual finds it
    scenarios = [
        {"id": "s1", "input": {"question": "q1", "expected": "pos"}, "expected_behavior": ""},
        {"id": "s2", "input": {"question": "q2", "expected": "pos"}, "expected_behavior": ""},
        {"id": "s3", "input": {"question": "q3", "expected": "neg"}, "expected_behavior": ""},
    ]
    (data_dir / "scenarios.json").write_text(json.dumps(scenarios))

    return tmp_path


def _make_processor_results(variant_id: str = "claude-test") -> List[OutputRecord]:
    """Three OutputRecords: s1=pos(correct), s2=pos(correct), s3=neg(correct) → accuracy=1.0."""
    ts = datetime.now(timezone.utc).isoformat()
    return [
        OutputRecord(
            test_subject="default",
            variant_id=variant_id,
            scenario_id="s1",
            processor_output='{"label": "pos"}',
            timing_ms=100,
            tokens_prompt=10,
            tokens_completion=5,
            timestamp=ts,
        ),
        OutputRecord(
            test_subject="default",
            variant_id=variant_id,
            scenario_id="s2",
            processor_output='{"label": "pos"}',
            timing_ms=110,
            tokens_prompt=10,
            tokens_completion=5,
            timestamp=ts,
        ),
        OutputRecord(
            test_subject="default",
            variant_id=variant_id,
            scenario_id="s3",
            processor_output='{"label": "neg"}',
            timing_ms=90,
            tokens_prompt=10,
            tokens_completion=5,
            timestamp=ts,
        ),
    ]


def _fake_evaluation_result(scenario_id: str, variant_id: str) -> EvaluationResult:
    return EvaluationResult(
        subject_id="default",
        variant_id=variant_id,
        scenario_id=scenario_id,
        processor_output='{"label": "pos"}',
        scenario_input="q1",
        judges=[
            JudgeEvaluation(
                judge_id="quality",
                score=8,
                reasoning="ok",
                evidence=None,
            )
        ],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
class TestJudgeRunnerMixed:
    """JudgeRunnerStep routes deterministic and LLM judges independently."""

    async def test_deterministic_metrics_populated(self, tmp_path: Path) -> None:
        """context.deterministic_metrics is set with ClassifierMetric results."""
        eval_root = _make_eval_dir(tmp_path)
        eval_ctx = LocalFileSystemEvalContext("mixed-judge-eval", eval_root=eval_root)
        run_ctx = LocalRunContext(
            eval_ctx,
            base_dir=tmp_path / "runs",
            run_id="run-mixed-001",
            snapshot=False,
        )
        run_ctx.processor_results = _make_processor_results()
        run_ctx.test_subject = "default"

        fake_results = [_fake_evaluation_result(sid, "claude-test") for sid in ["s1", "s2", "s3"]]

        logger = logging.getLogger("test")
        step = JudgeRunnerStep(logger)

        with patch(
            "gavel_ai.core.steps.judge_runner.JudgeExecutor.execute_batch",
            new=AsyncMock(return_value=fake_results),
        ):
            await step.execute(run_ctx)

        assert run_ctx.deterministic_metrics is not None
        assert "label_acc" in run_ctx.deterministic_metrics
        metric = run_ctx.deterministic_metrics["label_acc"]
        assert metric.population_score == pytest.approx(1.0)
        assert len(metric.samples) == 3

    async def test_llm_evaluation_results_populated(self, tmp_path: Path) -> None:
        """context.evaluation_results is populated from the LLM judge."""
        eval_root = _make_eval_dir(tmp_path)
        eval_ctx = LocalFileSystemEvalContext("mixed-judge-eval", eval_root=eval_root)
        run_ctx = LocalRunContext(
            eval_ctx,
            base_dir=tmp_path / "runs",
            run_id="run-mixed-002",
            snapshot=False,
        )
        run_ctx.processor_results = _make_processor_results()
        run_ctx.test_subject = "default"

        fake_results = [_fake_evaluation_result(sid, "claude-test") for sid in ["s1", "s2", "s3"]]

        logger = logging.getLogger("test")
        step = JudgeRunnerStep(logger)

        with patch(
            "gavel_ai.core.steps.judge_runner.JudgeExecutor.execute_batch",
            new=AsyncMock(return_value=fake_results),
        ):
            await step.execute(run_ctx)

        assert run_ctx.evaluation_results is not None
        assert len(run_ctx.evaluation_results) == 3

    async def test_deterministic_samples_have_correct_matches(self, tmp_path: Path) -> None:
        """Each sample in deterministic_metrics has correct match flag."""
        eval_root = _make_eval_dir(tmp_path)
        eval_ctx = LocalFileSystemEvalContext("mixed-judge-eval", eval_root=eval_root)
        run_ctx = LocalRunContext(
            eval_ctx,
            base_dir=tmp_path / "runs",
            run_id="run-mixed-003",
            snapshot=False,
        )
        run_ctx.processor_results = _make_processor_results()
        run_ctx.test_subject = "default"

        fake_results = [_fake_evaluation_result(sid, "claude-test") for sid in ["s1", "s2", "s3"]]

        logger = logging.getLogger("test")
        step = JudgeRunnerStep(logger)

        with patch(
            "gavel_ai.core.steps.judge_runner.JudgeExecutor.execute_batch",
            new=AsyncMock(return_value=fake_results),
        ):
            await step.execute(run_ctx)

        samples = run_ctx.deterministic_metrics["label_acc"].samples
        sample_map = {s.scenario_id: s for s in samples}
        assert sample_map["s1"].match is True   # pos == pos
        assert sample_map["s2"].match is True   # pos == pos
        assert sample_map["s3"].match is True   # neg == neg
