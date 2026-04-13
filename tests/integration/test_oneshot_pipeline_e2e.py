"""
End-to-end integration tests for the OneShot pipeline.

Tests the full ScenarioProcessorStep pipeline using a real (tmp) filesystem
with a faked LLM provider call. Validates:
- Prompt loading from eval directory filesystem structure
- Jinja2 template rendering with scenario variables
- PromptInput creation and message construction
- Results written to context.processor_results

Directory structure created in tmp_path:
    {eval_name}/
    ├── config/
    │   ├── eval_config.json
    │   ├── agents.json
    │   └── prompts/
    │       └── {name}.toml
    └── data/
        └── scenarios.json
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext
from gavel_ai.core.exceptions import ConfigError
from gavel_ai.core.steps.scenario_processor import ScenarioProcessorStep


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def eval_name() -> str:
    return "test-eval"


@pytest.fixture
def model_data() -> Dict[str, Any]:
    return {
        "model_provider": "anthropic",
        "model_family": "claude",
        "model_version": "claude-test",
        "model_parameters": {"temperature": 0.0},
        "provider_auth": {"api_key": "sk-test"},
    }


@pytest.fixture
def eval_dir(tmp_path: Path, eval_name: str, model_data: Dict[str, Any]) -> Path:
    """
    Create the full evaluation directory structure in tmp_path.

    Returns the root directory (tmp_path), NOT the eval subdir.
    Use LocalFileSystemEvalContext(eval_name, eval_dir) with this.
    """
    config_dir = tmp_path / eval_name / "config"
    prompts_dir = config_dir / "prompts"
    data_dir = tmp_path / eval_name / "data"

    config_dir.mkdir(parents=True)
    prompts_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)

    # Minimal eval_config.json
    eval_config = {
        "eval_name": eval_name,
        "eval_type": "oneshot",
        "test_subject_type": "local",
        "test_subjects": [{"prompt_name": "default", "judges": []}],
        "variants": ["claude-test"],
        "scenarios": {"source": "file.local", "name": "scenarios.json"},
    }
    (config_dir / "eval_config.json").write_text(json.dumps(eval_config))

    # agents.json with model under claude-test key
    agents = {"_models": {"claude-test": model_data}}
    (config_dir / "agents.json").write_text(json.dumps(agents))

    # default.toml prompt template (v1 only, uses string.Template $var syntax)
    (prompts_dir / "default.toml").write_text(
        'v1 = "Extract headlines from $site: $html"'
    )

    # scenarios.json with two scenarios
    scenarios = [
        {"id": "s1", "input": {"site": "bbc.com", "html": "<h1>Top Story</h1>"}, "expected_behavior": ""},
        {"id": "s2", "input": {"site": "cnn.com", "html": "<h1>Breaking</h1>"}, "expected_behavior": ""},
    ]
    (data_dir / "scenarios.json").write_text(json.dumps(scenarios))

    return tmp_path


@pytest.fixture
def mock_llm_response() -> MagicMock:
    """Fake LLM response from ProviderFactory.call_agent."""
    result = MagicMock()
    result.output = '{"headlines": ["Top Story"]}'
    result.metadata = {
        "latency_ms": 100,
        "tokens": {"prompt": 50, "completion": 20, "total": 70},
    }
    return result


@pytest.fixture
def logger() -> logging.Logger:
    return logging.getLogger("test")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_run_ctx(
    eval_dir: Path,
    eval_name: str,
    tmp_path: Path,
    run_id: str = "run-e2e-001",
) -> LocalRunContext:
    """Construct real EvalContext + RunContext pointing at tmp_path."""
    eval_ctx = LocalFileSystemEvalContext(eval_name, eval_root=eval_dir)
    run_ctx = LocalRunContext(
        eval_ctx,
        base_dir=tmp_path / "runs",
        run_id=run_id,
        snapshot=False,  # skip snapshot to avoid reading extra files
    )
    return run_ctx


# ---------------------------------------------------------------------------
# Happy-path pipeline tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
class TestScenarioProcessorStepE2E:
    """Full pipeline: real filesystem, faked LLM, ScenarioProcessorStep."""

    async def test_processes_scenarios_and_stores_results(
        self,
        eval_dir: Path,
        eval_name: str,
        tmp_path: Path,
        mock_llm_response: MagicMock,
        logger: logging.Logger,
    ) -> None:
        """ScenarioProcessorStep produces an OutputRecord per scenario."""
        run_ctx = make_run_ctx(eval_dir, eval_name, tmp_path)

        with patch("gavel_ai.processors.prompt_processor.ProviderFactory") as MockFactory:
            instance = MockFactory.return_value
            instance.create_agent.return_value = MagicMock()
            instance.call_agent = AsyncMock(return_value=mock_llm_response)

            step = ScenarioProcessorStep(logger)
            await step.execute(run_ctx)

        # Two scenarios → two records
        assert run_ctx.processor_results is not None
        assert len(run_ctx.processor_results) == 2

    async def test_rendered_prompt_contains_scenario_variables(
        self,
        eval_dir: Path,
        eval_name: str,
        tmp_path: Path,
        logger: logging.Logger,
    ) -> None:
        """Template variables {{ scenario.site }} and {{ scenario.html }} are substituted."""
        run_ctx = make_run_ctx(eval_dir, eval_name, tmp_path)

        captured_prompts: List[str] = []

        async def capture_call(agent: Any, prompt: str, **kwargs: Any) -> MagicMock:
            captured_prompts.append(prompt)
            result = MagicMock()
            result.output = '{"headlines": []}'
            result.metadata = {"latency_ms": 10, "tokens": {"prompt": 5, "completion": 2}}
            return result

        with patch("gavel_ai.processors.prompt_processor.ProviderFactory") as MockFactory:
            instance = MockFactory.return_value
            instance.create_agent.return_value = MagicMock()
            instance.call_agent = capture_call

            step = ScenarioProcessorStep(logger)
            await step.execute(run_ctx)

        # Each scenario should have its values in the rendered prompt
        assert any("bbc.com" in p for p in captured_prompts), "bbc.com not in any prompt"
        assert any("cnn.com" in p for p in captured_prompts), "cnn.com not in any prompt"
        assert any("Top Story" in p for p in captured_prompts), "<h1>Top Story</h1> not rendered"
        assert any("Breaking" in p for p in captured_prompts), "<h1>Breaking</h1> not rendered"

    async def test_output_records_have_correct_scenario_ids(
        self,
        eval_dir: Path,
        eval_name: str,
        tmp_path: Path,
        mock_llm_response: MagicMock,
        logger: logging.Logger,
    ) -> None:
        """Each OutputRecord carries the scenario_id of its source scenario."""
        run_ctx = make_run_ctx(eval_dir, eval_name, tmp_path)

        with patch("gavel_ai.processors.prompt_processor.ProviderFactory") as MockFactory:
            instance = MockFactory.return_value
            instance.create_agent.return_value = MagicMock()
            instance.call_agent = AsyncMock(return_value=mock_llm_response)

            step = ScenarioProcessorStep(logger)
            await step.execute(run_ctx)

        ids = {r.scenario_id for r in run_ctx.processor_results}
        assert ids == {"s1", "s2"}

    async def test_output_records_have_llm_response(
        self,
        eval_dir: Path,
        eval_name: str,
        tmp_path: Path,
        mock_llm_response: MagicMock,
        logger: logging.Logger,
    ) -> None:
        """Each OutputRecord carries the LLM output string."""
        run_ctx = make_run_ctx(eval_dir, eval_name, tmp_path)

        with patch("gavel_ai.processors.prompt_processor.ProviderFactory") as MockFactory:
            instance = MockFactory.return_value
            instance.create_agent.return_value = MagicMock()
            instance.call_agent = AsyncMock(return_value=mock_llm_response)

            step = ScenarioProcessorStep(logger)
            await step.execute(run_ctx)

        for record in run_ctx.processor_results:
            assert record.processor_output == '{"headlines": ["Top Story"]}'

    async def test_context_test_subject_and_variant_set(
        self,
        eval_dir: Path,
        eval_name: str,
        tmp_path: Path,
        mock_llm_response: MagicMock,
        logger: logging.Logger,
    ) -> None:
        """After execution, context.test_subject and context.model_variant are populated."""
        run_ctx = make_run_ctx(eval_dir, eval_name, tmp_path)

        with patch("gavel_ai.processors.prompt_processor.ProviderFactory") as MockFactory:
            instance = MockFactory.return_value
            instance.create_agent.return_value = MagicMock()
            instance.call_agent = AsyncMock(return_value=mock_llm_response)

            step = ScenarioProcessorStep(logger)
            await step.execute(run_ctx)

        assert run_ctx.test_subject is not None
        assert run_ctx.model_variant is not None


# ---------------------------------------------------------------------------
# Prompt version resolution tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
class TestPromptVersionResolution:
    """Tests for prompt template version resolution ('latest', specific version)."""

    async def test_latest_resolves_to_highest_version(
        self,
        eval_dir: Path,
        eval_name: str,
        tmp_path: Path,
        logger: logging.Logger,
    ) -> None:
        """'default:latest' resolves to v2 when both v1 and v2 exist."""
        prompts_dir = eval_dir / eval_name / "config" / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        (prompts_dir / "default.toml").write_text(
            'v1 = "old prompt {{ scenario.site }}"\n'
            'v2 = "new prompt {{ scenario.site }}"\n'
        )

        run_ctx = make_run_ctx(eval_dir, eval_name, tmp_path)

        captured: List[str] = []

        async def capture(agent: Any, prompt: str, **kwargs: Any) -> MagicMock:
            captured.append(prompt)
            r = MagicMock()
            r.output = "ok"
            r.metadata = {"latency_ms": 1, "tokens": {"prompt": 1, "completion": 1}}
            return r

        with patch("gavel_ai.processors.prompt_processor.ProviderFactory") as MockFactory:
            instance = MockFactory.return_value
            instance.create_agent.return_value = MagicMock()
            instance.call_agent = capture

            step = ScenarioProcessorStep(logger)
            await step.execute(run_ctx)

        # All rendered prompts should come from v2 (the highest)
        assert all("new prompt" in p for p in captured), f"Expected v2 prompt, got: {captured}"

    async def test_specific_version_used_when_configured(
        self,
        eval_dir: Path,
        eval_name: str,
        tmp_path: Path,
        logger: logging.Logger,
    ) -> None:
        """A prompt_name like 'default:v1' pins to v1 even when v2 exists."""
        config_dir = eval_dir / eval_name / "config"
        prompts_dir = config_dir / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)

        # Write multi-version prompt
        (prompts_dir / "default.toml").write_text(
            'v1 = "v1 prompt {{ scenario.site }}"\n'
            'v2 = "v2 prompt {{ scenario.site }}"\n'
        )

        # Update eval_config to pin v1 explicitly
        eval_config = json.loads((config_dir / "eval_config.json").read_text())
        eval_config["test_subjects"][0]["prompt_name"] = "default:v1"
        (config_dir / "eval_config.json").write_text(json.dumps(eval_config))

        run_ctx = make_run_ctx(eval_dir, eval_name, tmp_path)

        captured: List[str] = []

        async def capture(agent: Any, prompt: str, **kwargs: Any) -> MagicMock:
            captured.append(prompt)
            r = MagicMock()
            r.output = "ok"
            r.metadata = {"latency_ms": 1, "tokens": {"prompt": 1, "completion": 1}}
            return r

        with patch("gavel_ai.processors.prompt_processor.ProviderFactory") as MockFactory:
            instance = MockFactory.return_value
            instance.create_agent.return_value = MagicMock()
            instance.call_agent = capture

            step = ScenarioProcessorStep(logger)
            await step.execute(run_ctx)

        assert all("v1 prompt" in p for p in captured), f"Expected v1 prompt, got: {captured}"


# ---------------------------------------------------------------------------
# Error case tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
class TestScenarioProcessorErrors:
    """Error handling: missing prompt file, missing version, bad config."""

    async def test_missing_prompt_file_raises_config_error(
        self,
        eval_dir: Path,
        eval_name: str,
        tmp_path: Path,
        logger: logging.Logger,
    ) -> None:
        """ConfigError raised when the prompt TOML file does not exist."""
        # Remove the prompt file that the fixture created
        prompt_file = eval_dir / eval_name / "config" / "prompts" / "default.toml"
        prompt_file.unlink()

        run_ctx = make_run_ctx(eval_dir, eval_name, tmp_path)

        step = ScenarioProcessorStep(logger)
        with pytest.raises(ConfigError, match="Failed to load prompt template"):
            await step.execute(run_ctx)

    async def test_missing_variant_raises_config_error(
        self,
        eval_dir: Path,
        eval_name: str,
        tmp_path: Path,
        logger: logging.Logger,
    ) -> None:
        """ConfigError raised when the configured variant is not in agents.json."""
        config_dir = eval_dir / eval_name / "config"
        eval_config = json.loads((config_dir / "eval_config.json").read_text())
        eval_config["variants"] = ["nonexistent-model"]
        (config_dir / "eval_config.json").write_text(json.dumps(eval_config))

        run_ctx = make_run_ctx(eval_dir, eval_name, tmp_path)

        with patch("gavel_ai.processors.prompt_processor.ProviderFactory"):
            step = ScenarioProcessorStep(logger)
            with pytest.raises(ConfigError, match="not found in _models or agents"):
                await step.execute(run_ctx)

    async def test_empty_scenarios_runs_without_error(
        self,
        eval_dir: Path,
        eval_name: str,
        tmp_path: Path,
        mock_llm_response: MagicMock,
        logger: logging.Logger,
    ) -> None:
        """Empty scenario list completes without error and produces empty results."""
        data_dir = eval_dir / eval_name / "data"
        (data_dir / "scenarios.json").write_text("[]")

        run_ctx = make_run_ctx(eval_dir, eval_name, tmp_path)

        with patch("gavel_ai.processors.prompt_processor.ProviderFactory") as MockFactory:
            instance = MockFactory.return_value
            instance.create_agent.return_value = MagicMock()
            instance.call_agent = AsyncMock(return_value=mock_llm_response)

            step = ScenarioProcessorStep(logger)
            await step.execute(run_ctx)

        assert run_ctx.processor_results == []


# ---------------------------------------------------------------------------
# Prompt template loading unit tests (with tmp filesystem)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestPromptLoadingFromFilesystem:
    """Unit-level tests for prompt file loading using a real tmp filesystem."""

    def test_prompt_loaded_from_eval_config_dir(self, tmp_path: Path) -> None:
        """get_prompt() reads from eval_root/{eval_name}/config/prompts/{name}.toml."""
        prompts_dir = tmp_path / "myeval" / "config" / "prompts"
        prompts_dir.mkdir(parents=True)
        (prompts_dir / "extraction.toml").write_text('v1 = "Extract from {{ scenario.html }}"')

        ctx = LocalFileSystemEvalContext("myeval", eval_root=tmp_path)
        result = ctx.get_prompt("extraction:v1")

        assert result == "Extract from {{ scenario.html }}"

    def test_prompt_latest_resolves_highest_version(self, tmp_path: Path) -> None:
        """get_prompt('name:latest') picks the numerically highest v* key."""
        prompts_dir = tmp_path / "myeval" / "config" / "prompts"
        prompts_dir.mkdir(parents=True)
        (prompts_dir / "test.toml").write_text(
            'v1 = "version one"\nv2 = "version two"\nv10 = "version ten"\n'
        )

        ctx = LocalFileSystemEvalContext("myeval", eval_root=tmp_path)
        result = ctx.get_prompt("test:latest")

        assert result == "version ten"  # v10 > v2 numerically

    def test_prompt_file_not_found_raises_resource_not_found(self, tmp_path: Path) -> None:
        """get_prompt() raises ResourceNotFoundError for non-existent TOML."""
        from gavel_ai.core.exceptions import ResourceNotFoundError

        (tmp_path / "myeval" / "config" / "prompts").mkdir(parents=True)
        ctx = LocalFileSystemEvalContext("myeval", eval_root=tmp_path)

        with pytest.raises(ResourceNotFoundError, match="not found"):
            ctx.get_prompt("missing:v1")

    def test_prompt_cached_after_first_load(self, tmp_path: Path) -> None:
        """Second call to get_prompt() returns cached value without re-reading disk."""
        prompts_dir = tmp_path / "myeval" / "config" / "prompts"
        prompts_dir.mkdir(parents=True)
        prompt_file = prompts_dir / "cached.toml"
        prompt_file.write_text('v1 = "original"')

        ctx = LocalFileSystemEvalContext("myeval", eval_root=tmp_path)
        first = ctx.get_prompt("cached:v1")

        # Mutate file on disk — cached value should still be "original"
        prompt_file.write_text('v1 = "mutated"')
        second = ctx.get_prompt("cached:v1")

        assert first == second == "original"
