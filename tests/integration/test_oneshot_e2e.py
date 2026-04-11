import json
import os
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

# Apply integration tag
pytestmark = pytest.mark.integration

from gavel_ai.cli.commands.oneshot import app
import gavel_ai.cli.commands.oneshot as oneshot
from gavel_ai.providers.factory import ProviderResult
from gavel_ai.judges.judge_registry import JudgeRegistry
from gavel_ai.judges.base import Judge
from gavel_ai.models.config import JudgeConfig
from gavel_ai.models.runtime import JudgeResult, EvaluationResult

runner = CliRunner()


class DummyExactMatchJudge(Judge):
    def __init__(self, config: JudgeConfig):
        self.config = config

    async def evaluate(self, scenario, subject_output, **kwargs) -> JudgeResult:
        return JudgeResult(judge_id="exact_match", metric_name="match", score=10.0, reasoning="fake match")


@pytest.fixture
def mock_llm():
    """Mock the LLM provider call to avoid network requests during integration."""
    JudgeRegistry.register("exact_match", DummyExactMatchJudge)

    with patch("gavel_ai.providers.factory.ProviderFactory.call_agent", new_callable=AsyncMock) as mock_agent:
        mock_agent.return_value = ProviderResult(
            output="Mocked LLM Response",
            metadata={"tokens": {"total": 10}, "latency_ms": 100}
        )
        yield mock_agent

    JudgeRegistry.clear()


def test_oneshot_full_lifecycle(monkeypatch, tmp_path, mock_llm, capsys):
    # Setup temporary eval root
    eval_root = tmp_path / ".gavel" / "evaluations"
    eval_root.mkdir(parents=True)
    monkeypatch.setattr(oneshot, "DEFAULT_EVAL_ROOT", eval_root)

    with capsys.disabled():
        # Phase 1: Create scaffold
        result = runner.invoke(app, ["create", "--eval", "integration_eval"])
        assert result.exit_code == 0
        assert "Created evaluation 'integration_eval'" in result.stdout

        eval_dir = eval_root / "integration_eval"
        assert eval_dir.exists()

        # Phase 1b: Populate with test data
        with open(eval_dir / "data" / "scenarios.jsonl", "w") as f:
            f.write(json.dumps({"id": "test_1", "text": "Scenario 1 input"}) + "\n")
            f.write(json.dumps({"id": "test_2", "text": "Scenario 2 input"}) + "\n")

        # Replace default judge to avoid actual LLM calls during integration test
        with open(eval_dir / "config" / "eval_config.json", "r") as f:
            config = json.load(f)
        config["test_subjects"][0]["judges"] = [{"name": "exact_match", "type": "exact_match"}]
        with open(eval_dir / "config" / "eval_config.json", "w") as f:
            json.dump(config, f)

        os.environ["OPENAI_API_KEY"] = "fake"

        # Phase 2: Execute Run
        result = runner.invoke(app, ["run", "--eval", "integration_eval"])
        if result.exit_code != 0:
            print(result.stdout)
            print(result.exception)
        assert result.exit_code == 0
        assert "Evaluation complete" in result.stdout

        # Extract Run ID from output
        run_id_line = [line for line in result.stdout.split("\n") if "Run ID:" in line]
        assert run_id_line, "Run ID not found in output"
        run_id = run_id_line[0].split("Run ID:")[-1].strip()

        # Verify run artifacts were created
        run_dir = eval_dir / "runs" / run_id
        assert run_dir.exists()
        assert (run_dir / "manifest.json").exists()
        assert (run_dir / "results_raw.jsonl").exists()

        # Phase 3: List Runs
        result = runner.invoke(app, ["list", "--eval", "integration_eval"])
        if result.exit_code != 0:
            print(result.stdout)
            print(result.exception)
        assert result.exit_code == 0
        assert run_id in result.stdout
        assert "integration_eval" in result.stdout

        # Phase 4: Milestone Tagging
        result = runner.invoke(app, ["milestone", "--run", run_id, "--comment", "Test Baseline"])
        if result.exit_code != 0:
            print(result.stdout)
            print(result.exception)
        assert result.exit_code == 0
        assert "marked as milestone" in result.stdout

        # Verify milestone in list
        result = runner.invoke(app, ["list", "--eval", "integration_eval"])
        assert "⭐ Test Baseline" in result.stdout

        # Phase 5: Re-Judging
        result = runner.invoke(app, ["judge", "--run", run_id])
        if result.exit_code != 0:
            print(result.stdout)
            print(result.exception)
        assert result.exit_code == 0
        assert "Completed judging" in result.stdout

        # Verify report was regenerated
        assert (run_dir / "report.html").exists()
