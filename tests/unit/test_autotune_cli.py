import pytest

pytestmark = pytest.mark.unit
"""Unit tests for gavel autotune create/run CLI commands."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import toml
from typer.testing import CliRunner

from gavel_ai.cli.main import app
from gavel_ai.models.config import EvalConfig

runner = CliRunner()


class TestAutotuneCreateCommand:
    """Test suite for the `gavel autotune create` command."""

    def test_create_basic_structure(self, tmp_path: Path) -> None:
        eval_name = "test_autotune_eval"
        result = runner.invoke(
            app, ["autotune", "create", "--eval", eval_name, "--eval-root", str(tmp_path)]
        )

        assert result.exit_code == 0
        eval_dir = tmp_path / eval_name
        assert (eval_dir / "config" / "agents.json").exists()
        assert (eval_dir / "config" / "eval_config.json").exists()
        assert (eval_dir / "config" / "judges" / "quality_judge.toml").exists()
        assert (eval_dir / "config" / "prompts" / f"{eval_name}.toml").exists()
        assert (eval_dir / "data" / "scenarios.json").exists()

    def test_eval_config_is_valid_autotune_config(self, tmp_path: Path) -> None:
        eval_name = "test_autotune_eval"
        runner.invoke(app, ["autotune", "create", "--eval", eval_name, "--eval-root", str(tmp_path)])

        eval_config_file = tmp_path / eval_name / "config" / "eval_config.json"
        raw = json.loads(eval_config_file.read_text())

        assert raw["workflow_type"] == "autotune"
        assert raw["eval_type"] == "autotune"
        assert "tuning" in raw

        config = EvalConfig(**raw)
        assert config.workflow_type == "autotune"
        assert config.tuning is not None
        assert config.tuning.max_rounds == 5

    def test_prompts_toml_has_placeholder(self, tmp_path: Path) -> None:
        eval_name = "test_autotune_eval"
        runner.invoke(app, ["autotune", "create", "--eval", eval_name, "--eval-root", str(tmp_path)])

        prompts_file = tmp_path / eval_name / "config" / "prompts" / f"{eval_name}.toml"
        prompts = toml.loads(prompts_file.read_text())
        assert "v1" in prompts
        assert "{{input}}" in prompts["v1"]

    def test_scenarios_json_has_sample_scenarios(self, tmp_path: Path) -> None:
        eval_name = "test_autotune_eval"
        runner.invoke(app, ["autotune", "create", "--eval", eval_name, "--eval-root", str(tmp_path)])

        scenarios = json.loads((tmp_path / eval_name / "data" / "scenarios.json").read_text())
        assert len(scenarios) >= 1
        for scenario in scenarios:
            assert "scenario_id" in scenario
            assert "input" in scenario
            assert "expected" in scenario

    def test_create_fails_if_directory_exists(self, tmp_path: Path) -> None:
        eval_name = "test_autotune_eval"

        result1 = runner.invoke(
            app, ["autotune", "create", "--eval", eval_name, "--eval-root", str(tmp_path)]
        )
        assert result1.exit_code == 0

        result2 = runner.invoke(
            app, ["autotune", "create", "--eval", eval_name, "--eval-root", str(tmp_path)]
        )
        assert result2.exit_code != 0
        output = (result2.stdout + result2.stderr).lower()
        assert "already exists" in output

    def test_create_force_overwrites_existing(self, tmp_path: Path) -> None:
        eval_name = "test_autotune_eval"

        result1 = runner.invoke(
            app, ["autotune", "create", "--eval", eval_name, "--eval-root", str(tmp_path)]
        )
        assert result1.exit_code == 0

        result2 = runner.invoke(
            app,
            ["autotune", "create", "--eval", eval_name, "--eval-root", str(tmp_path), "--force"],
        )
        assert result2.exit_code == 0

    def test_create_validates_eval_name(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            ["autotune", "create", "--eval", "bad name with spaces", "--eval-root", str(tmp_path)],
        )
        assert result.exit_code != 0


class TestAutotuneRunCommand:
    """Test suite for the `gavel autotune run` command (workflow execution mocked)."""

    def _write_run_summary(self, run_dir: Path) -> None:
        run_dir.mkdir(parents=True, exist_ok=True)
        summary = {
            "eval_name": "test_autotune_eval",
            "run_id": "run-123",
            "total_iterations": 1,
            "best_iteration": 1,
            "best_score": 0.9,
            "final_score": 0.9,
            "converged": True,
            "convergence_reason": "max_rounds_reached",
            "iterations": [
                {
                    "iteration": 1,
                    "prompt_version": "v1",
                    "score": 0.9,
                    "improvement": 0.0,
                    "judge_scores": {"quality": 0.9},
                    "converged": True,
                    "convergence_reason": "max_rounds_reached",
                }
            ],
        }
        (run_dir / "run_summary.json").write_text(json.dumps(summary))
        (run_dir / "report.html").write_text("<html></html>")

    def test_run_invokes_workflow_execute_once(self, tmp_path: Path) -> None:
        eval_name = "test_autotune_eval"
        eval_root = tmp_path
        (eval_root / eval_name).mkdir(parents=True)

        run_dir = eval_root / eval_name / "runs" / "run-123"
        self._write_run_summary(run_dir)

        fake_run_ctx = MagicMock()
        fake_run_ctx.run_id = "run-123"
        fake_run_ctx.run_dir = run_dir

        with patch("gavel_ai.cli.commands.autotune.LocalFileSystemEvalContext"), patch(
            "gavel_ai.cli.commands.autotune.AutotuneWorkflow"
        ) as mock_workflow_cls:
            mock_workflow = MagicMock()
            mock_workflow.execute = AsyncMock(return_value=fake_run_ctx)
            mock_workflow.run_ctx = fake_run_ctx
            mock_workflow_cls.return_value = mock_workflow

            result = runner.invoke(
                app,
                ["autotune", "run", "--eval", eval_name, "--eval-root", str(eval_root)],
            )

        assert result.exit_code == 0, result.stdout
        mock_workflow.execute.assert_awaited_once_with(resume_run_id=None)
        assert "run-123" in result.stdout
        assert "report.html" in result.stdout

    def test_run_passes_resume_run_id(self, tmp_path: Path) -> None:
        eval_name = "test_autotune_eval"
        eval_root = tmp_path
        (eval_root / eval_name).mkdir(parents=True)

        run_dir = eval_root / eval_name / "runs" / "run-456"
        self._write_run_summary(run_dir)

        fake_run_ctx = MagicMock()
        fake_run_ctx.run_id = "run-456"
        fake_run_ctx.run_dir = run_dir

        with patch("gavel_ai.cli.commands.autotune.LocalFileSystemEvalContext"), patch(
            "gavel_ai.cli.commands.autotune.AutotuneWorkflow"
        ) as mock_workflow_cls:
            mock_workflow = MagicMock()
            mock_workflow.execute = AsyncMock(return_value=fake_run_ctx)
            mock_workflow.run_ctx = fake_run_ctx
            mock_workflow_cls.return_value = mock_workflow

            result = runner.invoke(
                app,
                [
                    "autotune",
                    "run",
                    "--eval",
                    eval_name,
                    "--eval-root",
                    str(eval_root),
                    "--run",
                    "run-456",
                ],
            )

        assert result.exit_code == 0, result.stdout
        mock_workflow.execute.assert_awaited_once_with(resume_run_id="run-456")

    def test_run_prints_error_panel_on_failure(self, tmp_path: Path) -> None:
        eval_name = "test_autotune_eval"
        eval_root = tmp_path
        (eval_root / eval_name).mkdir(parents=True)

        with patch("gavel_ai.cli.commands.autotune.LocalFileSystemEvalContext"), patch(
            "gavel_ai.cli.commands.autotune.AutotuneWorkflow"
        ) as mock_workflow_cls:
            mock_workflow = MagicMock()
            mock_workflow.execute = AsyncMock(side_effect=RuntimeError("boom"))
            mock_workflow.run_ctx = None
            mock_workflow_cls.return_value = mock_workflow

            result = runner.invoke(
                app,
                ["autotune", "run", "--eval", eval_name, "--eval-root", str(eval_root)],
            )

        assert result.exit_code != 0
        assert "Run failed" in result.stdout or "boom" in (result.stdout + result.stderr)
