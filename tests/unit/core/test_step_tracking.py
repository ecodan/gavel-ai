"""Unit tests for step tracking via .workflow_status."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

pytestmark = pytest.mark.unit


def make_run_context(tmp_path: Path):
    """Create a LocalRunContext with a real temp directory."""
    from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext
    from unittest.mock import MagicMock

    eval_ctx = MagicMock(spec=LocalFileSystemEvalContext)
    eval_ctx.eval_name = "test_eval"
    eval_ctx.config_dir = tmp_path / "config"
    eval_ctx.config_dir.mkdir(parents=True)

    # Mock data sources
    eval_ctx.eval_config.read.return_value = MagicMock()
    eval_ctx.agents.read.return_value = {"_models": {}}
    eval_ctx.scenarios.read.return_value = []

    base_dir = tmp_path / "runs"
    run_ctx = LocalRunContext(eval_ctx, base_dir=base_dir, run_id="run-test", snapshot=False)
    return run_ctx


class TestStepTracking:
    def test_workflow_status_created_on_mark(self, tmp_path):
        ctx = make_run_context(tmp_path)
        from gavel_ai.core.steps.base import StepPhase
        ctx.mark_step_complete(StepPhase.VALIDATION)
        status_file = ctx.run_dir / ".workflow_status"
        assert status_file.exists()

    def test_prepare_entry_exists(self, tmp_path):
        """When snapshot=True, PREPARE entry is written after snapshot_run_config."""
        from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext
        from gavel_ai.core.steps.base import StepPhase

        eval_ctx = MagicMock(spec=LocalFileSystemEvalContext)
        eval_ctx.eval_name = "test_eval"
        eval_ctx.config_dir = tmp_path / "config"
        eval_ctx.config_dir.mkdir(parents=True)
        eval_ctx.eval_config.read.return_value = MagicMock()
        eval_ctx.agents.read.return_value = {}
        eval_ctx.scenarios.read.return_value = []

        base_dir = tmp_path / "runs"
        # snapshot=True triggers snapshot_run_config + mark_step_complete(PREPARE)
        with patch.object(LocalRunContext, "snapshot_run_config", return_value=None):
            ctx = LocalRunContext(eval_ctx, base_dir=base_dir, run_id="run-test", snapshot=True)

        completed = ctx.get_completed_steps()
        assert StepPhase.PREPARE in completed

    def test_step_entry_on_safe_execute_success(self, tmp_path):
        from gavel_ai.core.steps.base import Step, StepPhase
        from gavel_ai.core.contexts import RunContext

        ctx = make_run_context(tmp_path)

        class DummyStep(Step):
            @property
            def phase(self):
                return StepPhase.VALIDATION

            async def execute(self, context):
                pass  # success

        import asyncio
        step = DummyStep(MagicMock())
        asyncio.get_event_loop().run_until_complete(step.safe_execute(ctx))

        assert StepPhase.VALIDATION in ctx.get_completed_steps()

    def test_no_entry_on_failure(self, tmp_path):
        from gavel_ai.core.steps.base import Step, StepPhase
        from gavel_ai.core.exceptions import ConfigError

        ctx = make_run_context(tmp_path)

        class FailStep(Step):
            @property
            def phase(self):
                return StepPhase.VALIDATION

            async def execute(self, context):
                raise ConfigError("intentional failure")

        import asyncio
        step = FailStep(MagicMock())
        result = asyncio.get_event_loop().run_until_complete(step.safe_execute(ctx))
        assert result is False
        assert StepPhase.VALIDATION not in ctx.get_completed_steps()

    def test_get_completed_steps_returns_empty_when_no_file(self, tmp_path):
        ctx = make_run_context(tmp_path)
        assert ctx.get_completed_steps() == []

    def test_get_completed_steps_order(self, tmp_path):
        from gavel_ai.core.steps.base import StepPhase
        ctx = make_run_context(tmp_path)
        ctx.mark_step_complete(StepPhase.PREPARE)
        ctx.mark_step_complete(StepPhase.VALIDATION)
        steps = ctx.get_completed_steps()
        assert steps[0] == StepPhase.PREPARE
        assert steps[1] == StepPhase.VALIDATION
