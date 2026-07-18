"""End-to-end integration test: `oneshot create --type external` then `oneshot run`
against the generated script-transport scaffold as a real subprocess.

Verifies the closed-box CLI path (config-driven external target inside `oneshot`,
not a separate command group) actually works out of the box with no manual editing.
"""
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

pytestmark = pytest.mark.integration

from gavel_ai.cli.commands.oneshot import app
from gavel_ai.judges.base import Judge
from gavel_ai.judges.judge_registry import JudgeRegistry
from gavel_ai.models.config import JudgeConfig
from gavel_ai.models.runtime import JudgeResult

runner = CliRunner()


class DummyPassJudge(Judge):
    def __init__(self, config: JudgeConfig):
        self.config = config

    async def evaluate(self, scenario, subject_output, **kwargs) -> JudgeResult:
        return JudgeResult(judge_id="dummy_pass", metric_name="pass", score=1.0, reasoning="ok")


@pytest.fixture
def dummy_judge():
    saved_registry: dict = dict(JudgeRegistry._registry)
    JudgeRegistry.register("dummy_pass", DummyPassJudge)
    yield
    JudgeRegistry._registry.clear()
    JudgeRegistry._registry.update(saved_registry)


def test_external_script_scaffold_runs_end_to_end(monkeypatch, tmp_path, dummy_judge, capsys):
    eval_root = tmp_path / ".gavel" / "evaluations"
    eval_root.mkdir(parents=True)
    monkeypatch.setattr("gavel_ai.cli.commands.oneshot.resolve_eval_root", lambda _: eval_root)

    with capsys.disabled():
        result = runner.invoke(app, ["create", "--eval", "ext_script_eval", "--type", "external"])
        assert result.exit_code == 0, result.stdout

        eval_dir = eval_root / "ext_script_eval"
        assert (eval_dir / "scripts" / "sut_script_scaffold.py").exists()
        assert (eval_dir / "scripts" / "sut_http_scaffold.py").exists()

        # Swap the deepeval judge for a dummy that needs no LLM call.
        config_path = eval_dir / "config" / "eval_config.json"
        config = json.loads(config_path.read_text())
        assert config["test_subjects"][0]["system_id"] == "sut-script"
        config["test_subjects"][0]["judges"] = [{"name": "dummy_pass", "type": "dummy_pass"}]
        config_path.write_text(json.dumps(config))

        result = runner.invoke(app, ["run", "--eval", "ext_script_eval"])
        if result.exit_code != 0:
            print(result.stdout)
            print(result.exception)
        assert result.exit_code == 0
        assert "Evaluation complete" in result.stdout

        run_id_line = [line for line in result.stdout.split("\n") if "Run ID:" in line]
        assert run_id_line, "Run ID not found in output"
        run_id = run_id_line[0].split("Run ID:")[-1].strip()

        run_dir = eval_dir / "runs" / run_id
        results_raw = (run_dir / "results_raw.jsonl").read_text().strip().splitlines()
        assert len(results_raw) >= 1

        record = json.loads(results_raw[0])
        assert not record.get("error")
        assert "SUT response for scenario" in record["processor_output"]
