"""
Unit tests for PromptInputProcessor Phase 3.

Tests:
- Accepting PromptInput with rendered prompts
- Constructing messages from user/system prompts
- LLM calls with structured messages
- Error handling and retry logic
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.models.agents import ModelDefinition
from gavel_ai.models.runtime import ProcessorConfig, ProcessorResult, PromptInput
from gavel_ai.processors.prompt_processor import PromptInputProcessor


@pytest.fixture
def logger() -> logging.Logger:
    """Provide a logger for testing."""
    return logging.getLogger("test")


@pytest.fixture
def processor_config() -> ProcessorConfig:
    """Provide a ProcessorConfig for testing."""
    return ProcessorConfig(
        processor_type="prompt_input",
        parallelism=1,
        timeout_seconds=30,
        error_handling="fail_fast",
    )


@pytest.fixture
def model_def() -> ModelDefinition:
    """Provide a ModelDefinition for testing."""
    return ModelDefinition(
        model_provider="anthropic",
        model_family="claude",
        model_version="claude-4-5-sonnet-latest",
        model_parameters={"temperature": 0.7, "max_tokens": 4096},
        provider_auth={"api_key": "test-key"},
    )


@pytest.mark.unit
class TestPromptInputProcessor:
    """Test PromptInputProcessor functionality."""

    @pytest.mark.asyncio
    async def test_process_single_prompt_input(
        self, processor_config: ProcessorConfig, model_def: ModelDefinition
    ) -> None:
        """Test processing a single PromptInput."""
        with patch("gavel_ai.processors.prompt_processor.ProviderFactory"):
            processor = PromptInputProcessor(processor_config, model_def)

            # Mock the LLM call
            processor._call_llm = AsyncMock(
                return_value=('{"stories": []}', {"tokens": {"total": 100}, "latency_ms": 50})
            )

            inputs = [
                PromptInput(
                    id="scenario-1",
                    user="Extract headlines from HTML",
                    system=None,
                )
            ]

            result = await processor.process(inputs)

            assert '{"stories": []}' in result.output
            assert result.metadata["input_count"] == 1

    @pytest.mark.asyncio
    async def test_process_with_system_prompt(
        self, processor_config: ProcessorConfig, model_def: ModelDefinition
    ) -> None:
        """Test processing PromptInput with system prompt."""
        with patch("gavel_ai.processors.prompt_processor.ProviderFactory"):
            processor = PromptInputProcessor(processor_config, model_def)

            processor._call_llm = AsyncMock(
                return_value=('Analysis result', {"tokens": {"total": 200}, "latency_ms": 100})
            )

            inputs = [
                PromptInput(
                    id="scenario-2",
                    user="Analyze this content",
                    system="You are an expert analyzer",
                )
            ]

            result = await processor.process(inputs)

            assert "Analysis result" in result.output
            # Verify _call_llm was called with messages
            processor._call_llm.assert_called_once()
            messages = processor._call_llm.call_args[0][0]
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_process_multiple_inputs(
        self, processor_config: ProcessorConfig, model_def: ModelDefinition
    ) -> None:
        """Test processing multiple PromptInput instances."""
        with patch("gavel_ai.processors.prompt_processor.ProviderFactory"):
            processor = PromptInputProcessor(processor_config, model_def)

            processor._call_llm = AsyncMock(
                return_value=('Result', {"tokens": {"total": 50}, "latency_ms": 25})
            )

            inputs = [
                PromptInput(id="s1", user="Prompt 1"),
                PromptInput(id="s2", user="Prompt 2"),
                PromptInput(id="s3", user="Prompt 3"),
            ]

            result = await processor.process(inputs)

            assert result.metadata["input_count"] == 3
            # All outputs should be combined
            assert "Result" in result.output

    @pytest.mark.asyncio
    async def test_message_construction_user_only(
        self, processor_config: ProcessorConfig, model_def: ModelDefinition
    ) -> None:
        """Test message construction with user prompt only."""
        with patch("gavel_ai.processors.prompt_processor.ProviderFactory"):
            processor = PromptInputProcessor(processor_config, model_def)

            call_args_list = []

            async def mock_call_llm(messages):
                call_args_list.append(messages)
                return ('Output', {})

            processor._call_llm = mock_call_llm

            inputs = [PromptInput(id="s1", user="Test prompt", system=None)]

            await processor.process(inputs)

            messages = call_args_list[0]
            assert len(messages) == 1
            assert messages[0]["role"] == "user"
            assert messages[0]["content"] == "Test prompt"

    @pytest.mark.asyncio
    async def test_message_construction_with_system(
        self, processor_config: ProcessorConfig, model_def: ModelDefinition
    ) -> None:
        """Test message construction with both system and user."""
        with patch("gavel_ai.processors.prompt_processor.ProviderFactory"):
            processor = PromptInputProcessor(processor_config, model_def)

            call_args_list = []

            async def mock_call_llm(messages):
                call_args_list.append(messages)
                return ('Output', {})

            processor._call_llm = mock_call_llm

            inputs = [
                PromptInput(
                    id="s1",
                    user="User message",
                    system="System message",
                )
            ]

            await processor.process(inputs)

            messages = call_args_list[0]
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == "System message"
            assert messages[1]["role"] == "user"
            assert messages[1]["content"] == "User message"

    @pytest.mark.asyncio
    async def test_metadata_aggregation(
        self, processor_config: ProcessorConfig, model_def: ModelDefinition
    ) -> None:
        """Test metadata aggregation across multiple inputs."""
        with patch("gavel_ai.processors.prompt_processor.ProviderFactory"):
            processor = PromptInputProcessor(processor_config, model_def)

            processor._call_llm = AsyncMock(
                return_value=(
                    'Output',
                    {"tokens": {"total": 150}, "latency_ms": 75, "model": "claude-v1"},
                )
            )

            inputs = [
                PromptInput(id="s1", user="P1"),
                PromptInput(id="s2", user="P2"),
            ]

            result = await processor.process(inputs)

            assert result.metadata["input_count"] == 2
            assert result.metadata["total_tokens"] == 300  # 150 * 2
            assert result.metadata["total_latency_ms"] == 150  # 75 * 2
            assert result.metadata.get("model") == "claude-v1"

    @pytest.mark.asyncio
    async def test_error_on_llm_failure(
        self, processor_config: ProcessorConfig, model_def: ModelDefinition
    ) -> None:
        """Test error handling on LLM call failure."""
        with patch("gavel_ai.processors.prompt_processor.ProviderFactory"):
            processor = PromptInputProcessor(processor_config, model_def)

            processor._call_llm = AsyncMock(
                side_effect=ProcessorError("LLM call failed")
            )

            inputs = [PromptInput(id="s1", user="Test")]

            # ProcessorError from _call_llm is re-raised directly
            with pytest.raises(ProcessorError, match="LLM call failed"):
                await processor.process(inputs)

    @pytest.mark.asyncio
    async def test_error_message_includes_input_id(
        self, processor_config: ProcessorConfig, model_def: ModelDefinition
    ) -> None:
        """Test that error messages include the input ID for debugging."""
        with patch("gavel_ai.processors.prompt_processor.ProviderFactory"):
            processor = PromptInputProcessor(processor_config, model_def)

            processor._call_llm = AsyncMock(
                side_effect=Exception("Test error")
            )

            inputs = [PromptInput(id="specific-scenario-123", user="Test")]

            with pytest.raises(ProcessorError) as exc_info:
                await processor.process(inputs)

            assert "specific-scenario-123" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_output_combination_single(
        self, processor_config: ProcessorConfig, model_def: ModelDefinition
    ) -> None:
        """Test output combination with single input."""
        with patch("gavel_ai.processors.prompt_processor.ProviderFactory"):
            processor = PromptInputProcessor(processor_config, model_def)

            processor._call_llm = AsyncMock(return_value=("Single output", {}))

            inputs = [PromptInput(id="s1", user="Prompt")]
            result = await processor.process(inputs)

            assert result.output == "Single output"

    @pytest.mark.asyncio
    async def test_output_combination_multiple(
        self, processor_config: ProcessorConfig, model_def: ModelDefinition
    ) -> None:
        """Test output combination with multiple inputs."""
        with patch("gavel_ai.processors.prompt_processor.ProviderFactory"):
            processor = PromptInputProcessor(processor_config, model_def)

            processor._call_llm = AsyncMock(return_value=("Output", {}))

            inputs = [
                PromptInput(id="s1", user="P1"),
                PromptInput(id="s2", user="P2"),
                PromptInput(id="s3", user="P3"),
            ]
            result = await processor.process(inputs)

            # Should be joined with "\n\n"
            assert result.output == "Output\n\nOutput\n\nOutput"
