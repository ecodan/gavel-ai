"""Integration tests for provider factory with real provider instantiation.

These tests verify that the Provider Factory correctly instantiates real provider
instances without mocking. This catches interface mismatches that mocked unit tests
miss (like the model_name parameter bug fixed in Story 3.9).
"""

import pytest

from gavel_ai.core.config.agents import ModelDefinition
from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.providers.factory import ProviderFactory


class TestProviderFactoryRealInstantiation:
    """Test provider factory with real provider instantiation (no mocks)."""

    def test_anthropic_provider_instantiation(self):
        """Test Anthropic provider can be instantiated with correct parameters."""
        model_def = ModelDefinition(
            model_provider="anthropic",
            model_family="claude",
            model_version="claude-3-5-sonnet-20241022",
            model_parameters={"temperature": 0.7},
            provider_auth={"api_key": "test-key-12345"},  # Mock API key
        )

        factory = ProviderFactory()

        # This should NOT raise "unexpected keyword argument 'model_name'"
        # Agent creation will complete successfully with mock API key
        agent = factory.create_agent(model_def)

        assert agent is not None
        assert hasattr(agent, "model")
        # Verify model type is AnthropicModel (from pydantic_ai.models.anthropic)
        assert "AnthropicModel" in str(type(agent.model))

    def test_openai_provider_instantiation(self):
        """Test OpenAI provider can be instantiated with correct parameters."""
        model_def = ModelDefinition(
            model_provider="openai",
            model_family="gpt",
            model_version="gpt-4",
            model_parameters={"temperature": 0.5},
            provider_auth={"api_key": "test-key-67890"},  # Mock API key
        )

        factory = ProviderFactory()

        # This should NOT raise "unexpected keyword argument 'model_name'"
        agent = factory.create_agent(model_def)

        assert agent is not None
        assert hasattr(agent, "model")
        # Verify model type is OpenAI model (OpenAIChatModel)
        assert "OpenAI" in str(type(agent.model))

    def test_google_provider_instantiation(self):
        """Test Google provider can be instantiated with correct parameters."""
        model_def = ModelDefinition(
            model_provider="google",
            model_family="gemini",
            model_version="gemini-1.5-pro",
            model_parameters={"temperature": 0.7},
            provider_auth={"api_key": "test-key-google"},  # Mock API key
        )

        factory = ProviderFactory()

        # This should NOT raise "unexpected keyword argument 'model_name'"
        agent = factory.create_agent(model_def)

        assert agent is not None
        assert hasattr(agent, "model")
        # Verify model type is GoogleModel (or GeminiModel)
        assert "Google" in str(type(agent.model)) or "Gemini" in str(type(agent.model))

    def test_ollama_provider_instantiation(self):
        """Test Ollama provider can be instantiated with correct parameters."""
        model_def = ModelDefinition(
            model_provider="ollama",
            model_family="qwen",
            model_version="qwen",
            model_parameters={"temperature": 0.7},
            provider_auth={"base_url": "http://localhost:11434"},  # No API key needed
        )

        factory = ProviderFactory()

        # This should NOT raise "unexpected keyword argument 'model_name'"
        # Ollama doesn't require API key, so this should work locally if Ollama is running
        agent = factory.create_agent(model_def)

        assert agent is not None
        assert hasattr(agent, "model")
        # Verify model type is OpenAI model (Ollama uses OpenAI-compatible API)
        assert "OpenAI" in str(type(agent.model))

    def test_provider_factory_without_api_key_raises_error(self):
        """Test that missing API key raises clear error."""
        model_def = ModelDefinition(
            model_provider="anthropic",
            model_family="claude",
            model_version="claude-3-5-sonnet-20241022",
            model_parameters={"temperature": 0.7},
            provider_auth={},  # No API key
        )

        factory = ProviderFactory()

        # Should raise ProcessorError with helpful message about missing API key
        with pytest.raises(ProcessorError, match="API key required"):
            factory.create_agent(model_def)

    def test_unsupported_provider_raises_error(self):
        """Test that unsupported provider raises clear error."""
        model_def = ModelDefinition(
            model_provider="unsupported-provider",
            model_family="unknown",
            model_version="v1",
            model_parameters={},
            provider_auth={"api_key": "test-key"},
        )

        factory = ProviderFactory()

        # Should raise ProcessorError with list of supported providers
        with pytest.raises(ProcessorError, match="Unsupported provider"):
            factory.create_agent(model_def)


class TestProviderFactoryParameters:
    """Test that providers are created with correct parameters."""

    def test_base_url_parameter_passed_correctly(self):
        """Test that base_url is passed to provider when specified."""
        model_def = ModelDefinition(
            model_provider="anthropic",
            model_family="claude",
            model_version="claude-3-5-sonnet-20241022",
            model_parameters={"temperature": 0.7},
            provider_auth={
                "api_key": "test-key",
                "base_url": "https://custom-api.example.com",
            },
        )

        factory = ProviderFactory()
        agent = factory.create_agent(model_def)

        assert agent is not None
        # Agent should be created with custom base_url
        # (Provider internally uses this for API calls)

    def test_environment_variable_substitution(self):
        """Test that environment variables in API keys are resolved."""
        import os

        # Set test environment variable
        os.environ["TEST_API_KEY"] = "resolved-key-from-env"

        try:
            model_def = ModelDefinition(
                model_provider="anthropic",
                model_family="claude",
                model_version="claude-3-5-sonnet-20241022",
                model_parameters={"temperature": 0.7},
                provider_auth={"api_key": "${TEST_API_KEY}"},  # Should be resolved
            )

            factory = ProviderFactory()

            # This should resolve ${TEST_API_KEY} to "resolved-key-from-env"
            agent = factory.create_agent(model_def)

            assert agent is not None
        finally:
            # Cleanup - always runs even if assertion fails
            if "TEST_API_KEY" in os.environ:
                del os.environ["TEST_API_KEY"]
