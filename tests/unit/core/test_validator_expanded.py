"""Unit tests for expanded ValidatorStep checks using real tmp-dir contexts."""
import asyncio
import json
import logging
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def write_eval_files(
    tmp_path: Path,
    eval_name: str = "test-eval",
    test_subject_type: str = "local",
    variants: list = None,
    models: dict = None,
    agents_extra: dict = None,
    prompt_name: str = "assistant",
    judges: list = None,
    scenarios: list = None,
    write_prompt: bool = True,
) -> Path:
    """
    Write a minimal but real eval directory under tmp_path.

    Returns the eval_root path (parent of eval_name dir).
    """
    if variants is None:
        variants = ["base-model"]
    if models is None:
        models = {"base-model": {"model_version": "gpt-4", "model_family": "gpt"}}
    if judges is None:
        judges = []
    if scenarios is None:
        scenarios = [{"scenario_id": "s1", "input": "hello"}]

    eval_root = tmp_path / "evaluations"
    eval_dir = eval_root / eval_name

    config_dir = eval_dir / "config"
    config_dir.mkdir(parents=True)
    (eval_dir / "data").mkdir(parents=True)
    (eval_dir / "runs").mkdir(parents=True)

    test_subject = {"prompt_name": prompt_name, "judges": judges}
    eval_config = {
        "eval_type": "oneshot",
        "eval_name": eval_name,
        "test_subject_type": test_subject_type,
        "test_subjects": [test_subject],
        "variants": variants,
        "scenarios": {"source": "file.local", "name": "scenarios.json"},
    }
    (config_dir / "eval_config.json").write_text(json.dumps(eval_config))

    agents_config: dict = {"_models": models}
    if agents_extra:
        agents_config.update(agents_extra)
    (config_dir / "agents.json").write_text(json.dumps(agents_config))

    (eval_dir / "data" / "scenarios.json").write_text(json.dumps(scenarios))

    if write_prompt:
        prompts_dir = config_dir / "prompts"
        prompts_dir.mkdir(parents=True)
        (prompts_dir / f"{prompt_name}.toml").write_text(
            "v1 = 'You are a helpful assistant. Input: {{input}}'\n"
        )

    return eval_root


def make_real_context(eval_root: Path, eval_name: str = "test-eval", run_id: str = "run-001"):
    """Return a real LocalRunContext backed by files in eval_root."""
    from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext

    eval_ctx = LocalFileSystemEvalContext(eval_name=eval_name, eval_root=eval_root)
    run_ctx = LocalRunContext(
        eval_ctx=eval_ctx,
        base_dir=eval_root / eval_name / "runs",
        run_id=run_id,
        snapshot=False,
    )
    return run_ctx


logger = logging.getLogger("test")


class TestValidatorExpanded:
    @pytest.mark.asyncio
    async def test_variant_direct_model_resolves(self, tmp_path):
        """Variant that matches a _models key directly passes validation."""
        from gavel_ai.core.steps.validator import ValidatorStep

        eval_root = write_eval_files(
            tmp_path,
            variants=["base-model"],
            models={"base-model": {"model_version": "gpt-4", "model_family": "gpt"}},
        )
        ctx = make_real_context(eval_root)
        step = ValidatorStep(logger)
        await step.execute(ctx)
        assert ctx.validation_result.is_valid is True

    @pytest.mark.asyncio
    async def test_variant_agent_reference_resolves(self, tmp_path):
        """Variant that is an agent pointing to a valid model passes validation."""
        from gavel_ai.core.steps.validator import ValidatorStep

        eval_root = write_eval_files(
            tmp_path,
            variants=["my-agent"],
            models={"base-model": {"model_version": "gpt-4", "model_family": "gpt"}},
            agents_extra={"my-agent": {"model_id": "base-model", "prompt": "assistant:v1"}},
            prompt_name="assistant",
            write_prompt=True,
        )
        ctx = make_real_context(eval_root)
        step = ValidatorStep(logger)
        await step.execute(ctx)
        assert ctx.validation_result.is_valid is True

    @pytest.mark.asyncio
    async def test_unknown_variant_raises(self, tmp_path):
        """Variant not in _models or agents raises ConfigError."""
        from gavel_ai.core.exceptions import ConfigError
        from gavel_ai.core.steps.validator import ValidatorStep

        eval_root = write_eval_files(
            tmp_path,
            variants=["unknown-variant"],
            models={"base-model": {"model_version": "gpt-4", "model_family": "gpt"}},
        )
        ctx = make_real_context(eval_root)
        step = ValidatorStep(logger)
        with pytest.raises(ConfigError, match="unknown-variant"):
            await step.execute(ctx)

    @pytest.mark.asyncio
    async def test_missing_prompt_raises(self, tmp_path):
        """Subject referencing a prompt file that doesn't exist raises ConfigError."""
        from gavel_ai.core.exceptions import ConfigError
        from gavel_ai.core.steps.validator import ValidatorStep

        eval_root = write_eval_files(
            tmp_path,
            variants=["base-model"],
            models={"base-model": {"model_version": "gpt-4", "model_family": "gpt"}},
            prompt_name="missing-prompt",
            write_prompt=False,
        )
        ctx = make_real_context(eval_root)
        step = ValidatorStep(logger)
        with pytest.raises(ConfigError, match="missing-prompt"):
            await step.execute(ctx)

    @pytest.mark.asyncio
    async def test_unregistered_judge_warns(self, tmp_path, caplog):
        """Unknown judge type emits a warning but does not raise."""
        from gavel_ai.core.steps.validator import ValidatorStep

        judges = [{"name": "j1", "type": "unregistered.type", "config": {}}]
        eval_root = write_eval_files(tmp_path, judges=judges)
        ctx = make_real_context(eval_root)
        step = ValidatorStep(logger)
        with caplog.at_level(logging.WARNING):
            await step.execute(ctx)
        assert any("unregistered.type" in m for m in caplog.messages)

    @pytest.mark.asyncio
    async def test_empty_scenarios_raises(self, tmp_path):
        """Empty scenarios file raises ValidationError."""
        from gavel_ai.core.exceptions import ValidationError
        from gavel_ai.core.steps.validator import ValidatorStep

        eval_root = write_eval_files(tmp_path, scenarios=[])
        ctx = make_real_context(eval_root)
        step = ValidatorStep(logger)
        with pytest.raises(ValidationError, match="No scenarios"):
            await step.execute(ctx)

    @pytest.mark.asyncio
    async def test_valid_config_passes(self, tmp_path):
        """Fully valid config passes all checks."""
        from gavel_ai.core.steps.validator import ValidatorStep

        eval_root = write_eval_files(tmp_path)
        ctx = make_real_context(eval_root)
        step = ValidatorStep(logger)
        await step.execute(ctx)
        assert ctx.validation_result.is_valid is True
