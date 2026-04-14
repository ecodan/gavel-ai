"""Unit tests for snapshot_run_config extensions and get_judge_config."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import toml

pytestmark = pytest.mark.unit


def _make_eval_config():
    from gavel_ai.models.config import EvalConfig, TestSubject, ScenariosConfig
    return EvalConfig(
        eval_type="oneshot",
        eval_name="test_eval",
        test_subject_type="local",
        test_subjects=[TestSubject(prompt_name="assistant", judges=[])],
        variants=["model-a"],
        scenarios=ScenariosConfig(source="file.local", name="scenarios.json"),
    )


def make_eval_ctx(tmp_path: Path):
    from gavel_ai.core.contexts import LocalFileSystemEvalContext
    ctx = LocalFileSystemEvalContext.__new__(LocalFileSystemEvalContext)
    ctx._eval_name = "test_eval"
    ctx._eval_root = tmp_path / "evaluations"
    (ctx._eval_root / "test_eval" / "config" / "prompts").mkdir(parents=True)
    (ctx._eval_root / "test_eval" / "config" / "judges").mkdir(parents=True)
    (ctx._eval_root / "test_eval" / "data").mkdir(parents=True)
    from gavel_ai.core.adapters.backends import LocalStorageBackend
    ctx._storage = LocalStorageBackend(ctx._eval_root / "test_eval")
    ctx._prompt_cache = {}
    ctx._judge_cache = {}
    return ctx


class TestSnapshotConfig:
    def test_prompts_copied_to_config(self, tmp_path):
        from gavel_ai.core.contexts import LocalRunContext
        eval_ctx = MagicMock()
        eval_ctx.eval_name = "test_eval"
        eval_ctx.config_dir = tmp_path / "config"
        eval_ctx.config_dir.mkdir(parents=True)
        prompts_dir = eval_ctx.config_dir / "prompts"
        prompts_dir.mkdir()
        (prompts_dir / "assistant.toml").write_text('[v1 = "hello"]')

        eval_ctx.eval_config.read.return_value = _make_eval_config()
        eval_ctx.agents.read.return_value = {"_models": {"model-a": {}}}
        eval_ctx.scenarios.read.return_value = []

        base_dir = tmp_path / "runs"
        ctx = LocalRunContext(eval_ctx, base_dir=base_dir, run_id="run-snap", snapshot=False)
        ctx.snapshot_run_config()

        assert (ctx.run_dir / ".config" / "prompts" / "assistant.toml").exists()

    def test_snapshot_metadata_written(self, tmp_path):
        from gavel_ai.core.contexts import LocalRunContext
        eval_ctx = MagicMock()
        eval_ctx.eval_name = "test_eval"
        eval_ctx.config_dir = tmp_path / "config"
        eval_ctx.config_dir.mkdir(parents=True)
        (eval_ctx.config_dir / "prompts").mkdir()

        eval_ctx.eval_config.read.return_value = _make_eval_config()
        eval_ctx.agents.read.return_value = {"_models": {"model-a": {}}}
        eval_ctx.scenarios.read.return_value = []

        base_dir = tmp_path / "runs"
        ctx = LocalRunContext(eval_ctx, base_dir=base_dir, run_id="run-snap", snapshot=False)
        ctx.snapshot_run_config()

        meta_path = ctx.run_dir / ".config" / "snapshot_metadata.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text())
        assert "snapshotted_at" in meta
        assert "files" in meta

    def test_silent_skip_when_no_prompts_dir(self, tmp_path):
        from gavel_ai.core.contexts import LocalRunContext
        eval_ctx = MagicMock()
        eval_ctx.eval_name = "test_eval"
        eval_ctx.config_dir = tmp_path / "config"
        eval_ctx.config_dir.mkdir(parents=True)
        # No prompts dir created

        eval_ctx.eval_config.read.return_value = _make_eval_config()
        eval_ctx.agents.read.return_value = {"_models": {"model-a": {}}}
        eval_ctx.scenarios.read.return_value = []

        base_dir = tmp_path / "runs"
        ctx = LocalRunContext(eval_ctx, base_dir=base_dir, run_id="run-snap", snapshot=False)
        ctx.snapshot_run_config()  # Should not raise


class TestGetJudgeConfig:
    def test_returns_dict_from_toml(self, tmp_path):
        from gavel_ai.core.contexts import LocalFileSystemEvalContext
        eval_ctx = LocalFileSystemEvalContext.__new__(LocalFileSystemEvalContext)
        eval_ctx._eval_name = "test_eval"
        eval_ctx._eval_root = tmp_path / "evaluations"
        judges_dir = eval_ctx._eval_root / "test_eval" / "config" / "judges"
        judges_dir.mkdir(parents=True)
        toml_content = {"criteria": "quality", "threshold": 0.7, "evaluation_steps": ["step1"]}
        (judges_dir / "quality_judge.toml").write_text(toml.dumps(toml_content))

        result = eval_ctx.get_judge_config("quality_judge")
        assert result["criteria"] == "quality"
        assert result["threshold"] == 0.7

    def test_raises_config_error_on_missing(self, tmp_path):
        from gavel_ai.core.contexts import LocalFileSystemEvalContext
        from gavel_ai.core.exceptions import ConfigError
        eval_ctx = LocalFileSystemEvalContext.__new__(LocalFileSystemEvalContext)
        eval_ctx._eval_name = "test_eval"
        eval_ctx._eval_root = tmp_path / "evaluations"
        judges_dir = eval_ctx._eval_root / "test_eval" / "config" / "judges"
        judges_dir.mkdir(parents=True)

        with pytest.raises(ConfigError):
            eval_ctx.get_judge_config("nonexistent")


class TestConfigRefResolution:
    """config_ref field in judge configs is resolved via get_judge_config() in JudgeRunnerStep."""

    def _write_eval(self, tmp_path: Path) -> Path:
        """Write a minimal eval with a quality_judge.toml and return eval_root."""
        eval_root = tmp_path / "evaluations"
        eval_dir = eval_root / "test-eval"
        judges_dir = eval_dir / "config" / "judges"
        judges_dir.mkdir(parents=True)
        (eval_dir / "config").mkdir(exist_ok=True)
        (eval_dir / "data").mkdir(parents=True)

        toml_data = {"criteria": "Answer quality", "threshold": 0.8}
        (judges_dir / "quality_judge.toml").write_text(toml.dumps(toml_data))

        return eval_root

    @pytest.mark.asyncio
    async def test_config_ref_merged_into_judge_config(self, tmp_path):
        """config_ref is loaded from TOML and merged into judge_config.config."""
        import asyncio
        import json
        from gavel_ai.core.contexts import LocalFileSystemEvalContext
        from gavel_ai.models.config import JudgeConfig

        eval_root = self._write_eval(tmp_path)
        eval_ctx = LocalFileSystemEvalContext(eval_name="test-eval", eval_root=eval_root)

        judge = JudgeConfig(name="quality", type="deepeval.geval", config_ref="quality_judge")

        # Simulate the config_ref resolution block from JudgeRunnerStep
        toml_data = eval_ctx.get_judge_config(judge.config_ref)
        if judge.config is None:
            judge.config = {}
        judge.config.update(toml_data)

        assert judge.config["criteria"] == "Answer quality"
        assert judge.config["threshold"] == pytest.approx(0.8)

    @pytest.mark.asyncio
    async def test_config_ref_missing_raises_config_error(self, tmp_path):
        """Referencing a nonexistent TOML via config_ref raises ConfigError."""
        from gavel_ai.core.contexts import LocalFileSystemEvalContext
        from gavel_ai.core.exceptions import ConfigError

        eval_root = self._write_eval(tmp_path)
        eval_ctx = LocalFileSystemEvalContext(eval_name="test-eval", eval_root=eval_root)

        with pytest.raises(ConfigError):
            eval_ctx.get_judge_config("nonexistent_judge")
