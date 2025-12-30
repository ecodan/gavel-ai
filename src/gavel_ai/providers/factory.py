"""
Provider factory for creating and calling Pydantic-AI agents.

Abstracts provider-specific configuration and provides unified interface for LLM calls.
"""

import os
import time
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent

from gavel_ai.core.config.agents import ModelDefinition
from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.telemetry import get_tracer

# Import provider classes for passing API keys
try:
    from pydantic_ai.providers.anthropic import AnthropicProvider
    from pydantic_ai.providers.openai import OpenAIProvider
    from pydantic_ai.providers.google import GoogleProvider
    from pydantic_ai.providers.ollama import OllamaProvider
except ImportError:
    # Fallback if provider imports change in future versions
    AnthropicProvider = None  # type: ignore
    OpenAIProvider = None  # type: ignore
    GoogleProvider = None  # type: ignore
    OllamaProvider = None  # type: ignore

tracer = get_tracer(__name__)


class ProviderResult(BaseModel):
    """Result from provider LLM call."""

    model_config = ConfigDict(extra="ignore")

    output: str
    metadata: Dict[str, Any] = {}


class ProviderFactory:
    """
    Factory for creating and calling Pydantic-AI agents.

    Per Architecture Decision 1: Pydantic-AI v1.39.0 provider abstraction.
    Supports: Anthropic (Claude), OpenAI (GPT), Google (Gemini), Ollama (local).
    """

    def __init__(self):
        """Initialize provider factory."""
        self.tracer = get_tracer(__name__)

    def create_agent(self, model_def: ModelDefinition) -> Agent:
        """
        Create Pydantic-AI agent from model definition.

        Args:
            model_def: Model definition with provider and configuration

        Returns:
            Configured Pydantic-AI Agent instance

        Raises:
            ProcessorError: If provider is unsupported or configuration invalid
        """
        with self.tracer.start_as_current_span("provider.create_agent") as span:
            span.set_attribute("provider", model_def.model_provider)
            span.set_attribute("model", model_def.model_version)

            # Extract API key or base URL from provider_auth
            api_key = model_def.provider_auth.get("api_key")
            base_url = model_def.provider_auth.get("base_url")

            # Resolve environment variables in API key
            if api_key and api_key.startswith("${") and api_key.endswith("}"):
                env_var_name = api_key[2:-1]
                api_key = os.getenv(env_var_name)

            # Create provider instance with credentials
            provider_instance = None

            try:
                if model_def.model_provider == "anthropic":
                    if AnthropicProvider is not None and api_key:
                        provider_instance = AnthropicProvider(
                            model_name=model_def.model_version,
                            api_key=api_key,
                        )
                    model_string = f"anthropic:{model_def.model_version}"

                elif model_def.model_provider == "openai":
                    if OpenAIProvider is not None and api_key:
                        provider_instance = OpenAIProvider(
                            model_name=model_def.model_version,
                            api_key=api_key,
                        )
                    model_string = f"openai:{model_def.model_version}"

                elif model_def.model_provider == "google":
                    if GoogleProvider is not None and api_key:
                        provider_instance = GoogleProvider(
                            model_name=model_def.model_version,
                            api_key=api_key,
                        )
                    model_string = f"google-genai:{model_def.model_version}"

                elif model_def.model_provider == "ollama":
                    if OllamaProvider is not None:
                        provider_instance = OllamaProvider(
                            model_name=model_def.model_version,
                            base_url=base_url or "http://localhost:11434",
                        )
                    model_string = f"ollama:{model_def.model_version}"

                else:
                    raise ProcessorError(
                        f"Unsupported provider '{model_def.model_provider}' - "
                        f"Supported providers: anthropic, openai, google, ollama"
                    )

                # Create agent with provider instance if available
                if provider_instance:
                    agent = Agent(model=provider_instance)
                else:
                    # Fallback to model string (requires env vars)
                    agent = Agent(model=model_string)

                return agent

            except ProcessorError:
                raise
            except Exception as e:
                raise ProcessorError(
                    f"Failed to create agent for provider '{model_def.model_provider}': {e} - "
                    f"Check provider_auth configuration and model version"
                ) from e

    async def call_agent(self, agent: Agent, prompt: str) -> ProviderResult:
        """
        Call agent with prompt and return result with metadata.

        Args:
            agent: Pydantic-AI Agent instance
            prompt: Prompt text to send to LLM

        Returns:
            ProviderResult with output and metadata

        Raises:
            ProcessorError: On LLM call failures
        """
        with self.tracer.start_as_current_span("provider.call_agent") as span:
            start_time = time.time()

            try:
                # Call agent
                response = await agent.run(prompt)

                # Extract output
                output = str(response.data)

                # Extract metadata
                metadata: Dict[str, Any] = {}

                # Tokens (if available)
                if hasattr(response, "usage") and response.usage:
                    metadata["tokens"] = {
                        "prompt": getattr(response.usage, "prompt_tokens", 0),
                        "completion": getattr(response.usage, "completion_tokens", 0),
                        "total": getattr(response.usage, "total_tokens", 0),
                    }
                else:
                    metadata["tokens"] = {"prompt": 0, "completion": 0, "total": 0}

                # Provider info
                # Extract provider from agent model
                model_str = str(agent.model) if hasattr(agent, "model") else "unknown"
                provider = model_str.split(":")[0] if ":" in model_str else "unknown"
                metadata["provider"] = provider
                metadata["model"] = model_str

                # Latency
                duration_ms = int((time.time() - start_time) * 1000)
                metadata["latency_ms"] = duration_ms

                span.set_attribute("llm.tokens.total", metadata["tokens"]["total"])
                span.set_attribute("llm.latency_ms", duration_ms)

                return ProviderResult(output=output, metadata=metadata)

            except TimeoutError as e:
                raise ProcessorError(
                    f"LLM call timed out - Increase timeout_seconds or check provider status"
                ) from e
            except Exception as e:
                raise ProcessorError(
                    f"LLM call failed: {e} - Check provider configuration and API key"
                ) from e
