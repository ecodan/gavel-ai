"""
End-to-end integration test for AutotuneWorkflow.

Runs a real (tmp filesystem) 2-round autotune loop with faked LLM provider,
judge executor, and tuning agent calls. Validates:
- Per-iteration artifacts (metadata.json, output_raw.jsonl) are written
- prompts.toml accumulates [v1] then [v2]
- run_summary.json reflects total_iterations=2
- report.html is rendered non-empty
- The tuned v2 prompt is actually used for iteration 2's scenario processing

Directory structure created in tmp_path:
    {eval_name}/
    ├── config/
    │   ├── eval_config.json   (workflow_type="autotune", tuning block, max_rounds=2)
    │   ├── agents.json
    │   └── prompts/
    │       └── {name}.toml    (v1 only — v2 is appended at runtime by TuneStep)
    └── data/
        └── scenarios.json
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import toml

from gavel_ai.core.contexts import LocalFileSystemEvalContext
from gavel_ai.core.workflows.autotune import AutotuneWorkflow
from gavel_ai.models.runtime import EvaluationResult, JudgeEvaluation

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

EVAL_NAME = "autotune-e2e"
PROMPT_NAME = "assistant"
V1_PROMPT = "Answer the question: {{question}}"
V2_PROMPT = "Improved! Answer the question carefully: {{question}}"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def eval_dir(tmp_path: Path) -> Path:
    """Scaffold a real autotune eval directory in tmp_path; returns the eval root."""
    config_dir = tmp_path / EVAL_NAME / "config"
    prompts_dir = config_dir / "prompts"
    data_dir = tmp_path / EVAL_NAME / "data"
    config_dir.mkdir(parents=True)
    prompts_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)

    eval_config = {
        "workflow_type": "autotune",
        "eval_name": EVAL_NAME,
        "eval_type": "autotune",
        "test_subject_type": "local",
        "test_subjects": [
            {
                "prompt_name": PROMPT_NAME,
                "judges": [
                    {
                        "name": "quality",
                        "type": "deepeval.geval",
                        "config": {
                            "criteria": "Is the answer correct?",
                            "evaluation_steps": ["Check correctness."],
                            "threshold": 0.5,
                            "model": "claude-test",
                        },
                    }
                ],
            }
        ],
        "variants": ["claude-test"],
        "scenarios": {"source": "file.local", "name": "scenarios.json"},
        "tuning": {
            "max_rounds": 2,
            "convergence_threshold": 0.02,
            "target_score": None,
            "degradation_tolerance": 0.05,
            "tuning_agent_model": "claude-test",
            "tuning_agent_temperature": 0.7,
        },
    }
    (config_dir / "eval_config.json").write_text(json.dumps(eval_config))

    agents = {
        "_models": {
            "claude-test": {
                "model_provider": "anthropic",
                "model_family": "claude",
                "model_version": "claude-test",
                "model_parameters": {"temperature": 0.0},
                "provider_auth": {"api_key": "sk-test"},
            }
        }
    }
    (config_dir / "agents.json").write_text(json.dumps(agents))

    (prompts_dir / f"{PROMPT_NAME}.toml").write_text(f'v1 = "{V1_PROMPT}"\n')

    scenarios = [
        {"id": "s1", "input": {"question": "What is 2+2?"}, "expected_behavior": "Answer '4'."},
        {
            "id": "s2",
            "input": {"question": "What is the capital of France?"},
            "expected_behavior": "Answer 'Paris'.",
        },
    ]
    (data_dir / "scenarios.json").write_text(json.dumps(scenarios))

    return tmp_path


def _fake_evaluation_results(scenario_ids: List[str], variant_id: str = "claude-test") -> List[EvaluationResult]:
    return [
        EvaluationResult(
            subject_id=PROMPT_NAME,
            variant_id=variant_id,
            scenario_id=scenario_id,
            processor_output="A reasonable answer.",
            scenario_input="q",
            judges=[JudgeEvaluation(judge_id="quality", score=0.8, reasoning="Looks correct", evidence=None)],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        for scenario_id in scenario_ids
    ]


@pytest.fixture
def logger() -> logging.Logger:
    return logging.getLogger("test")


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


class TestAutotuneWorkflowE2E:
    async def test_two_round_autotune_run_produces_expected_artifacts(
        self, eval_dir: Path, tmp_path: Path, logger: logging.Logger
    ) -> None:
        eval_ctx = LocalFileSystemEvalContext(EVAL_NAME, eval_root=eval_dir)

        captured_prompts: List[str] = []

        async def capture_call(agent: Any, prompt: str, **kwargs: Any) -> MagicMock:
            captured_prompts.append(prompt)
            result = MagicMock()
            result.output = "A reasonable answer."
            result.metadata = {"latency_ms": 10, "tokens": {"prompt": 5, "completion": 2}}
            return result

        fake_eval_results = _fake_evaluation_results(["s1", "s2"])

        tuning_agent_instance = MagicMock()
        tuning_agent_instance.generate_improved_prompt = AsyncMock(return_value=(V2_PROMPT, {"avg_score": 0.8}))

        with (
            patch("gavel_ai.processors.prompt_processor.ProviderFactory") as MockFactory,
            patch(
                "gavel_ai.core.steps.judge_runner.JudgeExecutor.execute_batch",
                new=AsyncMock(return_value=fake_eval_results),
            ),
            patch("gavel_ai.core.steps.tune_step.TuningAgent", return_value=tuning_agent_instance),
        ):
            instance = MockFactory.return_value
            instance.create_agent.return_value = MagicMock()
            instance.call_agent = capture_call

            workflow = AutotuneWorkflow(eval_ctx, logger)
            run_ctx = await workflow.execute()

        run_dir = run_ctx.run_dir
        iterations_dir = run_dir / "iterations"

        # --- Per-iteration artifacts ---
        for n in (1, 2):
            iter_dir = iterations_dir / f"iteration_{n}"
            assert (iter_dir / "metadata.json").exists(), f"missing metadata.json for iteration {n}"
            assert (iter_dir / "output_raw.jsonl").exists(), f"missing output_raw.jsonl for iteration {n}"

            metadata = json.loads((iter_dir / "metadata.json").read_text())
            assert metadata["iteration"] == n
            assert metadata["prompt_version"] == f"v{n}"

            raw_lines = (iter_dir / "output_raw.jsonl").read_text().strip().splitlines()
            assert len(raw_lines) == 2  # one record per scenario

        # iteration 2 is the max_rounds_reached convergence point
        iter2_metadata = json.loads((iterations_dir / "iteration_2" / "metadata.json").read_text())
        assert iter2_metadata["converged"] is True
        assert iter2_metadata["convergence_reason"] == "max_rounds_reached"

        # --- prompts.toml accumulation ---
        prompts_data: Dict[str, Any] = toml.load(str(run_dir / "prompts.toml"))
        assert "v1" in prompts_data and prompts_data["v1"]["prompt"] == V1_PROMPT
        assert "v2" in prompts_data and prompts_data["v2"]["prompt"] == V2_PROMPT
        assert "v3" not in prompts_data  # loop stopped at max_rounds; no further tuning

        # --- run_summary.json ---
        run_summary = json.loads((run_dir / "run_summary.json").read_text())
        assert run_summary["total_iterations"] == 2
        assert run_summary["converged"] is True
        assert run_summary["convergence_reason"] == "max_rounds_reached"
        assert len(run_summary["iterations"]) == 2

        # --- report.html ---
        report_path = run_dir / "report.html"
        assert report_path.exists()
        report_html = report_path.read_text(encoding="utf-8")
        assert len(report_html) > 0
        assert EVAL_NAME in report_html

        # --- v1 used for iteration 1, v2 used for iteration 2 ---
        v1_prompts = [p for p in captured_prompts if "Answer the question:" in p and "Improved!" not in p]
        v2_prompts = [p for p in captured_prompts if "Improved! Answer the question carefully:" in p]
        assert len(v1_prompts) == 2, f"expected 2 v1-rendered prompts, got: {captured_prompts}"
        assert len(v2_prompts) == 2, f"expected 2 v2-rendered prompts, got: {captured_prompts}"
        assert any("2+2" in p for p in v2_prompts)
        assert any("capital of France" in p for p in v2_prompts)
