"""Unit tests for TuningAgent and its meta-prompt rendering helpers."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gavel_ai.core.autotune.tuning_agent import (
    TuningAgent,
    _read_tuning_config,
    _render_meta_prompt,
)
from gavel_ai.providers.factory import ProviderResult

pytestmark = pytest.mark.unit


_AGENTS_CONFIG = {
    "_models": {
        "claude-standard": {
            "model_provider": "anthropic",
            "model_family": "claude",
            "model_version": "claude-4-5-sonnet-latest",
            "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
            "provider_auth": {"api_key": "test-key"},
        }
    }
}


def _make_eval_dir(tmp_path: Path, tuning_block: dict | None = None) -> Path:
    eval_dir = tmp_path / "test_eval"
    config_dir = eval_dir / "config"
    config_dir.mkdir(parents=True)
    if tuning_block is not None:
        (config_dir / "eval_config.json").write_text(
            json.dumps({"eval_name": "test_eval", "tuning": tuning_block})
        )
    return eval_dir


class TestRenderMetaPrompt:
    """Tests for the _render_meta_prompt {{var}} substitution helper."""

    def test_substitutes_known_variables(self) -> None:
        rendered = _render_meta_prompt(
            "Iteration {{iteration}} of {{max_rounds}}: {{current_prompt}}",
            {"iteration": 2, "max_rounds": 5, "current_prompt": "Hello {{name}}"},
        )
        assert rendered == "Iteration 2 of 5: Hello {{name}}"

    def test_passes_through_unknown_placeholders_unchanged(self) -> None:
        rendered = _render_meta_prompt("Keep {{unknown}} as-is", {"known": "value"})
        assert rendered == "Keep {{unknown}} as-is"


class TestReadTuningConfig:
    """Tests for the best-effort _read_tuning_config reader."""

    def test_reads_tuning_block_from_eval_config(self, tmp_path) -> None:
        eval_dir = _make_eval_dir(tmp_path, tuning_block={"max_rounds": 5, "target_score": 0.9})
        result = _read_tuning_config(eval_dir)
        assert result == {"max_rounds": 5, "target_score": 0.9}

    def test_returns_empty_dict_when_file_missing(self, tmp_path) -> None:
        eval_dir = _make_eval_dir(tmp_path, tuning_block=None)
        assert _read_tuning_config(eval_dir) == {}

    def test_returns_empty_dict_when_tuning_block_absent(self, tmp_path) -> None:
        eval_dir = _make_eval_dir(tmp_path)
        (eval_dir / "config" / "eval_config.json").write_text(json.dumps({"eval_name": "x"}))
        assert _read_tuning_config(eval_dir) == {}

    def test_returns_empty_dict_on_invalid_json(self, tmp_path) -> None:
        eval_dir = _make_eval_dir(tmp_path)
        (eval_dir / "config" / "eval_config.json").write_text("{not valid json")
        assert _read_tuning_config(eval_dir) == {}


class TestTuningAgentInit:
    """Tests for TuningAgent construction and model resolution."""

    def test_raises_when_model_id_not_found(self) -> None:
        with pytest.raises(ValueError, match="not found in agents_config"):
            TuningAgent(model_id="missing-model", agents_config=_AGENTS_CONFIG)

    def test_applies_temperature_override(self) -> None:
        with patch("gavel_ai.core.autotune.tuning_agent.ProviderFactory") as mock_factory_cls:
            mock_factory = mock_factory_cls.return_value
            mock_factory.create_agent.return_value = MagicMock()

            agent = TuningAgent(
                model_id="claude-standard", agents_config=_AGENTS_CONFIG, temperature=1.5
            )

            assert agent.model_def.model_parameters["temperature"] == 1.5
            # max_tokens from the base model definition is preserved
            assert agent.model_def.model_parameters["max_tokens"] == 4096
            mock_factory.create_agent.assert_called_once_with(agent.model_def)

    def test_default_temperature_is_point_seven(self) -> None:
        with patch("gavel_ai.core.autotune.tuning_agent.ProviderFactory") as mock_factory_cls:
            mock_factory = mock_factory_cls.return_value
            mock_factory.create_agent.return_value = MagicMock()

            agent = TuningAgent(model_id="claude-standard", agents_config=_AGENTS_CONFIG)

            assert agent.model_def.model_parameters["temperature"] == 0.7


class TestGenerateImprovedPrompt:
    """Tests for TuningAgent.generate_improved_prompt()."""

    def _make_agent(self) -> TuningAgent:
        with patch("gavel_ai.core.autotune.tuning_agent.ProviderFactory") as mock_factory_cls:
            mock_factory = mock_factory_cls.return_value
            mock_factory.create_agent.return_value = MagicMock()
            agent = TuningAgent(model_id="claude-standard", agents_config=_AGENTS_CONFIG)
            agent.provider_factory = mock_factory
            return agent

    @pytest.mark.asyncio
    async def test_generates_prompt_and_returns_stripped_output_with_metadata(
        self, tmp_path
    ) -> None:
        eval_dir = _make_eval_dir(
            tmp_path, tuning_block={"max_rounds": 5, "target_score": 0.9, "tuning_agent_model": "claude-standard"}
        )
        agent = self._make_agent()
        agent.provider_factory.call_agent = AsyncMock(
            return_value=ProviderResult(
                output="  IMPROVED PROMPT {{input}}  \n",
                metadata={"tokens": {"total": 123}, "latency_ms": 45},
            )
        )

        current_prompt = "Answer the question: {{input}} using {{context}}"
        judge_feedback = [
            {"scenario_id": "s1", "judge_name": "similarity", "score": 0.8, "reason": "ok"},
            {"scenario_id": "s2", "judge_name": "similarity", "score": 0.6, "reason": "weak"},
        ]

        improved_prompt, metadata = await agent.generate_improved_prompt(
            current_prompt=current_prompt,
            judge_feedback=judge_feedback,
            iteration=2,
            eval_dir=eval_dir,
        )

        assert improved_prompt == "IMPROVED PROMPT {{input}}"
        assert metadata == {"tokens": {"total": 123}, "latency_ms": 45}

        # Inspect the rendered prompt passed to call_agent
        rendered_prompt = agent.provider_factory.call_agent.call_args[0][1]
        assert "iteration 2 of 5" in rendered_prompt
        assert "average score of 0.7" in rendered_prompt  # avg of 0.8 and 0.6
        assert "target: 0.9" in rendered_prompt
        assert "{{context}}, {{input}}" in rendered_prompt  # sorted placeholder_vars
        assert current_prompt in rendered_prompt
        assert json.dumps(judge_feedback) in rendered_prompt

    @pytest.mark.asyncio
    async def test_handles_missing_scores_and_tuning_config(self, tmp_path) -> None:
        """When judge_feedback has no numeric scores and no tuning block exists, uses safe defaults."""
        eval_dir = _make_eval_dir(tmp_path, tuning_block=None)
        agent = self._make_agent()
        agent.provider_factory.call_agent = AsyncMock(
            return_value=ProviderResult(output="NEW PROMPT", metadata={})
        )

        improved_prompt, _ = await agent.generate_improved_prompt(
            current_prompt="No placeholders here",
            judge_feedback=[{"scenario_id": "s1", "judge_name": "j", "reason": "no score field"}],
            iteration=1,
            eval_dir=eval_dir,
        )

        assert improved_prompt == "NEW PROMPT"
        rendered_prompt = agent.provider_factory.call_agent.call_args[0][1]
        assert "average score of 0.0" in rendered_prompt
        assert "target: none" in rendered_prompt
        assert "iteration 1 of unknown" in rendered_prompt

    @pytest.mark.asyncio
    async def test_uses_eval_local_meta_prompt_override(self, tmp_path) -> None:
        """An eval-local config/prompts/autotune.toml overrides the bundled meta-prompt template."""
        eval_dir = _make_eval_dir(tmp_path, tuning_block={"max_rounds": 3})
        prompts_dir = eval_dir / "config" / "prompts"
        prompts_dir.mkdir(parents=True)
        (prompts_dir / "autotune.toml").write_text(
            '[v1]\nprompt = """CUSTOM META PROMPT iteration {{iteration}}"""\n'
        )

        agent = self._make_agent()
        agent.provider_factory.call_agent = AsyncMock(
            return_value=ProviderResult(output="OUT", metadata={})
        )

        await agent.generate_improved_prompt(
            current_prompt="P", judge_feedback=[], iteration=1, eval_dir=eval_dir
        )

        rendered_prompt = agent.provider_factory.call_agent.call_args[0][1]
        assert rendered_prompt == "CUSTOM META PROMPT iteration 1"
