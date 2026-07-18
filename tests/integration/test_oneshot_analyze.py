"""Integration tests for `gavel oneshot analyze` against a real run directory."""
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from gavel_ai.cli.main import app
from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext
from gavel_ai.models.runtime import OutputRecord

pytestmark = pytest.mark.integration

runner = CliRunner()


def _record(scenario_id: str, timing_ms: int = 100, error: str | None = None) -> OutputRecord:
    return OutputRecord(
        test_subject="test-subject",
        variant_id="v1",
        scenario_id=scenario_id,
        processor_output="output",
        timing_ms=timing_ms,
        tokens_prompt=10,
        tokens_completion=5,
        error=error,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _create_eval_with_results(tmp_path: Path, eval_name: str, run_id: str) -> None:
    result = runner.invoke(
        app, ["oneshot", "create", "--eval", eval_name, "--eval-root", str(tmp_path)]
    )
    assert result.exit_code == 0, result.stdout

    eval_ctx = LocalFileSystemEvalContext(eval_name=eval_name, eval_root=tmp_path)
    run_ctx = LocalRunContext(
        eval_ctx=eval_ctx,
        base_dir=tmp_path / eval_name / "runs",
        run_id=run_id,
        snapshot=False,
    )
    run_ctx.results_raw.write(
        [_record("1", timing_ms=100), _record("2", timing_ms=200, error="boom")]
    )


class TestOneshotAnalyze:
    def test_analyze_prints_metrics_table(self, tmp_path: Path) -> None:
        _create_eval_with_results(tmp_path, "analyze_eval", "run-1")

        result = runner.invoke(
            app,
            [
                "oneshot",
                "analyze",
                "--run",
                "run-1",
                "--eval",
                "analyze_eval",
                "--eval-root",
                str(tmp_path),
            ],
        )

        assert result.exit_code == 0, result.stdout
        assert "Run metrics" in result.stdout
        assert "Scenarios" in result.stdout
        assert "Error rate" in result.stdout

    def test_analyze_missing_run_errors_cleanly(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app, ["oneshot", "create", "--eval", "no_run_eval", "--eval-root", str(tmp_path)]
        )
        assert result.exit_code == 0

        result = runner.invoke(
            app,
            [
                "oneshot",
                "analyze",
                "--run",
                "does-not-exist",
                "--eval",
                "no_run_eval",
                "--eval-root",
                str(tmp_path),
            ],
        )
        assert result.exit_code != 0
        output = (result.stdout + result.stderr).lower()
        assert "no results found" in output

    def test_analyze_works_by_run_id_without_eval_name(self, tmp_path: Path) -> None:
        _create_eval_with_results(tmp_path, "analyze_eval_2", "run-2")

        result = runner.invoke(
            app,
            ["oneshot", "analyze", "--run", "run-2", "--eval-root", str(tmp_path)],
        )
        assert result.exit_code == 0, result.stdout
        assert "Run metrics" in result.stdout
