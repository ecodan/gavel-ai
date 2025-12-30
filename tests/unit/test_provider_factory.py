"""
Unit tests for provider factory.

Tests Pydantic-AI integration and provider abstraction.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gavel_ai.core.config.agents import ModelDefinition
from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.providers.factory import ProviderFactory, ProviderResult


class TestProviderFactory:
    """Test provider factory initialization and configuration."""

    def test_factory_initialization(self):
        """Test factory can be initialized."""
        factory = ProviderFactory()
        assert factory is not None

    @patch("gavel_ai.providers.factory.AnthropicProvider")
    @patch("gavel_ai.providers.factory.Agent")
    def test_create_agent_with_anthropic_provider(self, MockAgent, MockAnthropicProvider):
        """Test creating agent with Anthropic provider."""
        model_def = ModelDefinition(
            model_provider="anthropic",
            model_family="claude",
            model_version="claude-3-5-sonnet-latest",
            model_parameters={"temperature": 0.7, "max_tokens": 4096},
            provider_auth={"api_key": "test-key"},
        )

        mock_provider = MagicMock()
        MockAnthropicProvider.return_value = mock_provider

        mock_agent = MagicMock()
        MockAgent.return_value = mock_agent

        factory = ProviderFactory()
        agent = factory.create_agent(model_def)

        assert agent is not None
        MockAnthropicProvider.assert_called_once_with(
            model_name="claude-3-5-sonnet-latest",
            api_key="test-key",
        )
        MockAgent.assert_called_once_with(model=mock_provider)

    @patch("gavel_ai.providers.factory.OpenAIProvider")
    @patch("gavel_ai.providers.factory.Agent")
    def test_create_agent_with_openai_provider(self, MockAgent, MockOpenAIProvider):
        """Test creating agent with OpenAI provider."""
        model_def = ModelDefinition(
            model_provider="openai",
            model_family="gpt",
            model_version="gpt-4",
            model_parameters={"temperature": 0.7, "max_tokens": 2000},
            provider_auth={"api_key": "test-key"},
        )

        mock_provider = MagicMock()
        MockOpenAIProvider.return_value = mock_provider

        mock_agent = MagicMock()
        MockAgent.return_value = mock_agent

        factory = ProviderFactory()
        agent = factory.create_agent(model_def)

        assert agent is not None
        MockOpenAIProvider.assert_called_once_with(
            model_name="gpt-4",
            api_key="test-key",
        )

    def test_create_agent_with_unsupported_provider_raises_error(self):
        """Test unsupported provider raises clear error."""
        model_def = ModelDefinition(
            model_provider="unsupported-provider",
            model_family="unknown",
            model_version="v1",
            model_parameters={},
            provider_auth={},
        )

        factory = ProviderFactory()

        with pytest.raises(ProcessorError, match="Unsupported provider"):
            factory.create_agent(model_def)


class TestProviderExecution:
    """Test provider execution and response handling."""

    @pytest.mark.asyncio
    async def test_call_agent_with_prompt(self):
        """Test calling agent with prompt returns result."""
        factory = ProviderFactory()

        # Create mock agent
        mock_agent = MagicMock()
        mock_agent.model = "anthropic:claude-3-5-sonnet-latest"

        mock_response = MagicMock()
        mock_response.data = "Test response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30

        mock_agent.run = AsyncMock(return_value=mock_response)

        result = await factory.call_agent(mock_agent, "Test prompt")

        assert isinstance(result, ProviderResult)
        assert result.output == "Test response"
        assert result.metadata["tokens"]["total"] == 30

    @pytest.mark.asyncio
    async def test_call_agent_extracts_metadata(self):
        """Test metadata extraction from provider response."""
        factory = ProviderFactory()

        # Create mock agent
        mock_agent = MagicMock()
        mock_agent.model = "anthropic:claude-3-5-sonnet-latest"

        mock_response = MagicMock()
        mock_response.data = "Response"
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 150

        mock_agent.run = AsyncMock(return_value=mock_response)

        result = await factory.call_agent(mock_agent, "Prompt")

        assert result.metadata["tokens"]["prompt"] == 50
        assert result.metadata["tokens"]["completion"] == 100
        assert result.metadata["tokens"]["total"] == 150
        assert result.metadata["provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_call_agent_handles_timeout_error(self):
        """Test timeout errors are wrapped properly."""
        factory = ProviderFactory()

        # Create mock agent that raises timeout
        mock_agent = MagicMock()
        mock_agent.model = "anthropic:claude-3-5-sonnet-latest"
        mock_agent.run = AsyncMock(side_effect=TimeoutError("Request timed out"))

        with pytest.raises(ProcessorError, match="timed out"):
            await factory.call_agent(mock_agent, "Prompt")

    @pytest.mark.asyncio
    async def test_call_agent_with_missing_usage_metadata(self):
        """Test handling responses without usage metadata."""
        factory = ProviderFactory()

        # Create mock agent with response missing usage
        mock_agent = MagicMock()
        mock_agent.model = "anthropic:claude-3-5-sonnet-latest"

        mock_response = MagicMock()
        mock_response.data = "Response without usage"
        mock_response.usage = None

        mock_agent.run = AsyncMock(return_value=mock_response)

        result = await factory.call_agent(mock_agent, "Prompt")

        assert result.output == "Response without usage"
        assert result.metadata["tokens"]["total"] == 0
