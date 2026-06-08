"""Unit tests for CompositeStep.run_children()."""
import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gavel_ai.core.steps.base import CompositeStep, Step, StepPhase
from gavel_ai.models.config import ErrorPolicy

pytestmark = pytest.mark.unit


def make_run_context(tmp_path: Path):
    """Create a LocalRunContext with a real temp directory (snapshot disabled)."""
    from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext

    eval_ctx = MagicMock(spec=LocalFileSystemEvalContext)
    eval_ctx.eval_name = "test_eval"
    eval_ctx.config_dir = tmp_path / "config"
    eval_ctx.config_dir.mkdir(parents=True)

    eval_ctx.eval_config.read.return_value = MagicMock()
    eval_ctx.agents.read.return_value = {"_models": {}}
    eval_ctx.scenarios.read.return_value = []

    base_dir = tmp_path / "runs"
    return LocalRunContext(eval_ctx, base_dir=base_dir, run_id="run-test", snapshot=False)


class RecordingStep(Step):
    """Step that records its own execution into a shared list and always succeeds."""

    def __init__(self, name: str, calls: list):
        super().__init__(logging.getLogger("test"))
        self._name = name
        self._calls = calls

    @property
    def phase(self) -> StepPhase:
        return StepPhase.AUTOTUNE_ITERATION

    async def execute(self, context) -> None:
        self._calls.append(self._name)


class FailingStep(Step):
    """Step that records its execution then raises a RuntimeError (classified as ERROR tier)."""

    def __init__(self, name: str, calls: list):
        super().__init__(logging.getLogger("test"))
        self._name = name
        self._calls = calls

    @property
    def phase(self) -> StepPhase:
        return StepPhase.AUTOTUNE_ITERATION

    async def execute(self, context) -> None:
        self._calls.append(self._name)
        raise RuntimeError(f"{self._name} failed")


class ConcreteCompositeStep(CompositeStep):
    """Minimal concrete CompositeStep for testing run_children()."""

    @property
    def phase(self) -> StepPhase:
        return StepPhase.TUNING

    async def execute(self, context) -> None:
        await self.run_children(context)


class TestCompositeStep:
    """Tests for CompositeStep.run_children()."""

    def test_phase_is_tuning(self) -> None:
        composite = ConcreteCompositeStep([], logging.getLogger("test"))
        assert composite.phase == StepPhase.TUNING

    @pytest.mark.asyncio
    async def test_run_children_runs_all_in_order(self, tmp_path) -> None:
        """All child steps run in declared order when each succeeds."""
        ctx = make_run_context(tmp_path)
        calls: list = []
        children = [RecordingStep("a", calls), RecordingStep("b", calls), RecordingStep("c", calls)]
        composite = ConcreteCompositeStep(children, logging.getLogger("test"))

        result = await composite.run_children(ctx)

        assert result is True
        assert calls == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_run_children_stops_on_first_failure(self, tmp_path) -> None:
        """Execution halts at the first child that fails; later children never run."""
        ctx = make_run_context(tmp_path)
        calls: list = []
        children = [
            RecordingStep("a", calls),
            FailingStep("b", calls),
            RecordingStep("c", calls),
        ]
        composite = ConcreteCompositeStep(children, logging.getLogger("test"))
        lenient_policy = ErrorPolicy(exit_on_error=False, exit_on_warning=False)

        result = await composite.run_children(ctx, error_policy=lenient_policy)

        assert result is False
        assert calls == ["a", "b"]

    @pytest.mark.asyncio
    async def test_run_children_empty_list_succeeds(self, tmp_path) -> None:
        """An empty child list trivially succeeds."""
        ctx = make_run_context(tmp_path)
        composite = ConcreteCompositeStep([], logging.getLogger("test"))

        result = await composite.run_children(ctx)

        assert result is True

    @pytest.mark.asyncio
    async def test_run_children_propagates_run_policy_error(self, tmp_path) -> None:
        """A strict error policy (exit_on_error=True, the default) raises RunPolicyError."""
        from gavel_ai.core.exceptions import RunPolicyError

        ctx = make_run_context(tmp_path)
        calls: list = []
        children = [FailingStep("a", calls), RecordingStep("b", calls)]
        composite = ConcreteCompositeStep(children, logging.getLogger("test"))
        strict_policy = ErrorPolicy(exit_on_error=True, exit_on_warning=False)

        with pytest.raises(RunPolicyError):
            await composite.run_children(ctx, error_policy=strict_policy)

        assert calls == ["a"]

    @pytest.mark.asyncio
    async def test_run_children_returns_false_without_raising_under_lenient_policy(
        self, tmp_path
    ) -> None:
        """A lenient policy (exit_on_error=False) surfaces failure as False, not an exception."""
        ctx = make_run_context(tmp_path)
        calls: list = []
        children = [FailingStep("a", calls), RecordingStep("b", calls)]
        composite = ConcreteCompositeStep(children, logging.getLogger("test"))
        lenient_policy = ErrorPolicy(exit_on_error=False, exit_on_warning=False)

        result = await composite.run_children(ctx, error_policy=lenient_policy)

        assert result is False
        assert calls == ["a"]
