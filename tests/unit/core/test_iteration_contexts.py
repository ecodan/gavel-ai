"""Unit tests for IterationEvalContext, IterationRunContext, and LocalRunContext snapshot skipping."""
import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


def _make_eval_config():
    from gavel_ai.models.config import EvalConfig, ScenariosConfig, TestSubject

    return EvalConfig(
        eval_type="oneshot",
        eval_name="test_eval",
        test_subject_type="local",
        test_subjects=[TestSubject(prompt_name="assistant", judges=[])],
        variants=["model-a"],
        scenarios=ScenariosConfig(source="file.local", name="scenarios.json"),
    )


def make_eval_ctx(tmp_path: Path):
    """Create a mocked LocalFileSystemEvalContext with a real config_dir on disk."""
    from gavel_ai.core.contexts import LocalFileSystemEvalContext

    eval_ctx = MagicMock(spec=LocalFileSystemEvalContext)
    eval_ctx.eval_name = "test_eval"
    eval_ctx.config_dir = tmp_path / "config"
    eval_ctx.config_dir.mkdir(parents=True)
    (eval_ctx.config_dir / "prompts").mkdir()

    eval_ctx.eval_config.read.return_value = _make_eval_config()
    eval_ctx.agents.read.return_value = {"_models": {"model-a": {}}}
    eval_ctx.scenarios.read.return_value = []
    eval_ctx.get_prompt.return_value = "BASE PROMPT v1 {{input}}"
    return eval_ctx


class TestIterationEvalContext:
    """Tests for IterationEvalContext.get_prompt() and attribute delegation."""

    def test_get_prompt_reads_version_from_run_local_toml(self, tmp_path) -> None:
        """When prompts.toml has the requested version section, its prompt text is returned."""
        from gavel_ai.core.contexts import IterationEvalContext

        prompts_toml_path = tmp_path / "prompts.toml"
        prompts_toml_path.write_text('[v2]\nprompt = "ITERATED PROMPT v2 {{input}}"\n')

        base = make_eval_ctx(tmp_path)
        ctx = IterationEvalContext(base=base, prompts_toml_path=prompts_toml_path, version="v2")

        assert ctx.get_prompt("assistant:latest") == "ITERATED PROMPT v2 {{input}}"
        base.get_prompt.assert_not_called()

    def test_get_prompt_falls_back_to_base_when_toml_missing(self, tmp_path) -> None:
        """When prompts.toml does not yet exist, get_prompt() delegates to the base context."""
        from gavel_ai.core.contexts import IterationEvalContext

        prompts_toml_path = tmp_path / "prompts.toml"
        assert not prompts_toml_path.exists()

        base = make_eval_ctx(tmp_path)
        ctx = IterationEvalContext(base=base, prompts_toml_path=prompts_toml_path, version="v1")

        assert ctx.get_prompt("assistant:latest") == "BASE PROMPT v1 {{input}}"
        base.get_prompt.assert_called_once_with("assistant:latest")

    def test_get_prompt_falls_back_to_base_when_version_section_missing(self, tmp_path) -> None:
        """When the requested version section is absent from prompts.toml, falls back to base."""
        from gavel_ai.core.contexts import IterationEvalContext

        prompts_toml_path = tmp_path / "prompts.toml"
        prompts_toml_path.write_text('[v1]\nprompt = "ORIGINAL"\n')

        base = make_eval_ctx(tmp_path)
        ctx = IterationEvalContext(base=base, prompts_toml_path=prompts_toml_path, version="v3")

        assert ctx.get_prompt("assistant:latest") == "BASE PROMPT v1 {{input}}"
        base.get_prompt.assert_called_once_with("assistant:latest")

    def test_attribute_access_delegates_to_base(self, tmp_path) -> None:
        """Attributes not defined on the wrapper delegate to the wrapped base context."""
        from gavel_ai.core.contexts import IterationEvalContext

        prompts_toml_path = tmp_path / "prompts.toml"
        base = make_eval_ctx(tmp_path)
        ctx = IterationEvalContext(base=base, prompts_toml_path=prompts_toml_path, version="v1")

        assert ctx.eval_name == "test_eval"
        assert ctx.config_dir == base.config_dir


class TestIterationRunContext:
    """Tests for the IterationRunContext dataclass."""

    def test_construction_and_field_access(self, tmp_path) -> None:
        from gavel_ai.core.contexts import IterationEvalContext, IterationRunContext

        prompts_toml_path = tmp_path / "prompts.toml"
        base = make_eval_ctx(tmp_path)
        eval_ctx = IterationEvalContext(base=base, prompts_toml_path=prompts_toml_path, version="v1")

        run_dir = tmp_path / "iterations" / "iteration_1"
        run_dir.mkdir(parents=True)
        results_raw = MagicMock()
        evaluation_results = MagicMock()

        ctx = IterationRunContext(
            eval_ctx=eval_ctx,
            run_id="run-001",
            run_logger=logging.getLogger("test"),
            run_dir=run_dir,
            results_raw=results_raw,
            evaluation_results=evaluation_results,
        )

        assert ctx.eval_ctx is eval_ctx
        assert ctx.run_id == "run-001"
        assert ctx.run_dir == run_dir
        assert ctx.last_step_error is None
        assert ctx.processor_results == []
        assert ctx.evaluation_results_data == []
        assert ctx.deterministic_metrics == {}

    def test_mark_step_complete_is_a_noop(self, tmp_path) -> None:
        """mark_step_complete() does nothing — the outer LocalRunContext owns step tracking."""
        from gavel_ai.core.contexts import IterationEvalContext, IterationRunContext
        from gavel_ai.core.steps.base import StepPhase

        prompts_toml_path = tmp_path / "prompts.toml"
        base = make_eval_ctx(tmp_path)
        eval_ctx = IterationEvalContext(base=base, prompts_toml_path=prompts_toml_path, version="v1")
        run_dir = tmp_path / "iterations" / "iteration_1"
        run_dir.mkdir(parents=True)

        ctx = IterationRunContext(
            eval_ctx=eval_ctx,
            run_id="run-001",
            run_logger=logging.getLogger("test"),
            run_dir=run_dir,
            results_raw=MagicMock(),
            evaluation_results=MagicMock(),
        )

        # Should not raise and should not create any tracking artifacts.
        ctx.mark_step_complete(StepPhase.AUTOTUNE_ITERATION)
        assert not (run_dir / ".workflow_status").exists()


class TestLocalRunContextSnapshotSkipping:
    """LocalRunContext's existing `snapshot` flag doubles as the spec's requested skip_snapshot."""

    def test_snapshot_true_writes_config_snapshot(self, tmp_path) -> None:
        from gavel_ai.core.contexts import LocalRunContext

        eval_ctx = make_eval_ctx(tmp_path)
        base_dir = tmp_path / "runs"

        ctx = LocalRunContext(eval_ctx, base_dir=base_dir, run_id="run-snap-on", snapshot=True)

        assert (ctx.run_dir / ".config").exists()

    def test_snapshot_false_skips_config_snapshot(self, tmp_path) -> None:
        """Passing snapshot=False (the autotune per-iteration use case) writes no .config side-effects."""
        from gavel_ai.core.contexts import LocalRunContext

        eval_ctx = make_eval_ctx(tmp_path)
        base_dir = tmp_path / "runs"

        ctx = LocalRunContext(eval_ctx, base_dir=base_dir, run_id="run-snap-off", snapshot=False)

        assert not (ctx.run_dir / ".config").exists()
