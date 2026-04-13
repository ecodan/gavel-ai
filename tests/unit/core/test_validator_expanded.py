"""Unit tests for expanded ValidatorStep checks."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

pytestmark = pytest.mark.unit


def make_context(
    test_subject_type="local",
    variants=None,
    models=None,
    agents_extra=None,
    prompt_name="assistant",
    judges=None,
    scenarios=None,
):
    from gavel_ai.models.config import EvalConfig, TestSubject, JudgeConfig, ScenariosConfig
    from gavel_ai.models.runtime import Scenario

    if variants is None:
        variants = ["model-a"]
    if models is None:
        models = {"model-a": {"model_version": "gpt-4", "model_family": "gpt"}}
    if judges is None:
        judges = []
    if scenarios is None:
        scenarios = [Scenario(id="s1", input={"text": "hello"})]

    agents_config = {"_models": models}
    if agents_extra:
        agents_config.update(agents_extra)

    subject = TestSubject(prompt_name=prompt_name, judges=judges)
    eval_config = EvalConfig(
        eval_type="oneshot",
        eval_name="test",
        test_subject_type=test_subject_type,
        test_subjects=[subject],
        variants=variants,
        scenarios=ScenariosConfig(source="file.local", name="scenarios.json"),
    )

    ctx = MagicMock()
    ctx.eval_context.eval_name = "test"
    ctx.eval_context.eval_config.read.return_value = eval_config
    ctx.eval_context.agents.read.return_value = agents_config
    ctx.eval_context.scenarios.read.return_value = scenarios
    ctx.eval_context.get_prompt.return_value = "prompt text"
    ctx.run_logger = MagicMock()
    return ctx


class TestValidatorExpanded:
    @pytest.mark.asyncio
    async def test_variant_direct_model_resolves(self):
        from gavel_ai.core.steps.validator import ValidatorStep
        ctx = make_context(variants=["model-a"], models={"model-a": {}})
        step = ValidatorStep(MagicMock())
        await step.execute(ctx)  # Should not raise

    @pytest.mark.asyncio
    async def test_variant_agent_reference_resolves(self):
        from gavel_ai.core.steps.validator import ValidatorStep
        ctx = make_context(
            variants=["my-agent"],
            models={"base-model": {}},
            agents_extra={"my-agent": {"model_id": "base-model"}},
        )
        step = ValidatorStep(MagicMock())
        await step.execute(ctx)

    @pytest.mark.asyncio
    async def test_unknown_variant_raises(self):
        from gavel_ai.core.steps.validator import ValidatorStep
        from gavel_ai.core.exceptions import ConfigError
        ctx = make_context(variants=["unknown-variant"], models={"model-a": {}})
        step = ValidatorStep(MagicMock())
        with pytest.raises(ConfigError, match="unknown-variant"):
            await step.execute(ctx)

    @pytest.mark.asyncio
    async def test_missing_prompt_raises(self):
        from gavel_ai.core.steps.validator import ValidatorStep
        from gavel_ai.core.exceptions import ConfigError
        ctx = make_context(prompt_name="missing_prompt")
        ctx.eval_context.get_prompt.side_effect = Exception("not found")
        step = ValidatorStep(MagicMock())
        with pytest.raises(ConfigError, match="missing_prompt"):
            await step.execute(ctx)

    @pytest.mark.asyncio
    async def test_unregistered_judge_warns(self):
        from gavel_ai.core.steps.validator import ValidatorStep
        from gavel_ai.models.config import JudgeConfig
        judge = JudgeConfig(name="j1", type="unregistered.type", config={})
        ctx = make_context(judges=[judge])
        step = ValidatorStep(MagicMock())
        await step.execute(ctx)  # Should not raise
        step.logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_empty_scenarios_raises(self):
        from gavel_ai.core.steps.validator import ValidatorStep
        from gavel_ai.core.exceptions import ValidationError
        ctx = make_context(scenarios=[])
        step = ValidatorStep(MagicMock())
        with pytest.raises(ValidationError, match="No scenarios"):
            await step.execute(ctx)

    @pytest.mark.asyncio
    async def test_valid_config_passes(self):
        from gavel_ai.core.steps.validator import ValidatorStep
        ctx = make_context()
        step = ValidatorStep(MagicMock())
        await step.execute(ctx)
        assert ctx.validation_result.is_valid is True
