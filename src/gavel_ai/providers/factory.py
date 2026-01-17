"""
Provider factory for creating and calling Pydantic-AI agents.

Abstracts provider-specific configuration and provides unified interface for LLM calls.
"""

import os
import time
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent, models
from pydantic_ai.providers import Provider

from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.models.agents import ModelDefinition
from gavel_ai.telemetry import get_current_run_id, get_metadata_collector, get_tracer

# Import provider classes for passing API keys
try:
    from pydantic_ai.providers.anthropic import AnthropicProvider
    from pydantic_ai.providers.google import GoogleProvider
    from pydantic_ai.providers.ollama import OllamaProvider
    from pydantic_ai.providers.openai import OpenAIProvider
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

    def create_agent(self, model_def: ModelDefinition, output_type: type = str) -> Agent:
        """
        Create Pydantic-AI agent from model definition with configurable output type.

        Args:
            model_def: Model definition with provider and configuration
            output_type: Expected output type - can be str (default), Pydantic model,
                        or built-in types. Use Pydantic models for structured outputs
                        (e.g., JudgeVerdict, EvaluationResult). Use str for raw text.

        Returns:
            Configured Pydantic-AI Agent instance

        Raises:
            ProcessorError: If provider is unsupported or configuration invalid

        Example:
            # Simple string output (default)
            agent = factory.create_agent(model_def)

            # Structured output with Pydantic model
            class JudgeVerdict(BaseModel):
                winner: Literal["subject", "baseline", "tie"]
                confidence: float
                reasoning: str

            agent = factory.create_agent(model_def, output_type=JudgeVerdict)
            result = await agent.run(prompt)
            verdict: JudgeVerdict = result.output  # Type-safe!
        """
        with self.tracer.start_as_current_span("provider.create_agent") as span:
            span.set_attribute("provider", model_def.model_provider)
            span.set_attribute("model", model_def.model_version)

            # Extract API key or base URL from provider_auth
            api_key = model_def.provider_auth.get("api_key")
            base_url = model_def.provider_auth.get("base_url")

            # Resolve environment variables in API key (supports {{VAR}} and ${VAR} formats)
            if api_key:
                env_var_name = None
                if api_key.startswith("{{") and api_key.endswith("}}"):
                    env_var_name = api_key[2:-2]
                elif api_key.startswith("${") and api_key.endswith("}"):
                    env_var_name = api_key[2:-1]

                if env_var_name:
                    resolved_key = os.getenv(env_var_name)
                    if not resolved_key:
                        from gavel_ai.core.exceptions import ConfigError

                        raise ConfigError(
                            f"Environment variable '{env_var_name}' not set - "
                            f"Set {env_var_name} or provide api_key directly in provider_auth"
                        )
                    api_key = resolved_key

            try:
                # Build model string: "provider:model_version"
                # This is used by models.infer_model() to select the correct model
                model_string = f"{model_def.model_provider}:{model_def.model_version}"

                # Create provider_factory function that returns configured provider instances
                # Providers are created with auth credentials ONLY (no model_name parameter)
                def provider_factory(provider_name: str) -> Provider:
                    """
                    Factory function for creating provider instances with credentials.

                    NOTE: Providers do NOT take model_name parameter.
                    Model selection happens via model_string passed to models.infer_model().

                    Parameter mapping:
                    - model_def.provider_auth['api_key'] → provider api_key parameter
                    - model_def.provider_auth['base_url'] → provider base_url parameter
                    - model_def.model_version → extracted from model_string by Pydantic-AI
                    """
                    if provider_name == "anthropic":
                        if AnthropicProvider is None:
                            raise ProcessorError(
                                "Anthropic provider not available - "
                                "Install pydantic-ai with anthropic support"
                            )
                        if not api_key:
                            raise ProcessorError(
                                "Anthropic API key required - "
                                "Set 'api_key' in provider_auth or ANTHROPIC_API_KEY env var"
                            )
                        # Anthropic provider: Only api_key and base_url parameters
                        return AnthropicProvider(
                            api_key=api_key,
                            base_url=base_url,
                        )

                    elif provider_name == "openai":
                        if OpenAIProvider is None:
                            raise ProcessorError(
                                "OpenAI provider not available - "
                                "Install pydantic-ai with openai support"
                            )
                        if not api_key:
                            raise ProcessorError(
                                "OpenAI API key required - "
                                "Set 'api_key' in provider_auth or OPENAI_API_KEY env var"
                            )
                        # OpenAI provider: Only api_key and base_url parameters
                        return OpenAIProvider(
                            api_key=api_key,
                            base_url=base_url,
                        )

                    elif provider_name == "google":
                        if GoogleProvider is None:
                            raise ProcessorError(
                                "Google provider not available - "
                                "Install pydantic-ai with google support"
                            )
                        if not api_key:
                            raise ProcessorError(
                                "Google API key required - "
                                "Set 'api_key' in provider_auth or GOOGLE_API_KEY env var"
                            )
                        # Google provider: Only api_key and base_url parameters
                        return GoogleProvider(
                            api_key=api_key,
                            base_url=base_url,
                        )

                    elif provider_name == "ollama":
                        if OllamaProvider is None:
                            raise ProcessorError(
                                "Ollama provider not available - "
                                "Install pydantic-ai with ollama support"
                            )
                        # Ollama provider: Only base_url parameter (no API key required)
                        return OllamaProvider(
                            base_url=base_url or "http://localhost:11434",
                        )

                    else:
                        raise ProcessorError(
                            f"Unsupported provider '{provider_name}' - "
                            f"Supported providers: anthropic, openai, google, ollama"
                        )

                # Create model using infer_model with custom provider_factory
                # This creates the correct Model subclass (AnthropicModel, OpenAIModel, etc.)
                # with the provider instance and model name combined
                model = models.infer_model(model_string, provider_factory=provider_factory)

                # Create agent with the configured model and output type
                # output_type can be str (default) for raw text or a Pydantic model for structured data
                agent = Agent(model=model, output_type=output_type)

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

                # Extract output (use .output, not deprecated .data)
                output = str(response.output)

                # Extract metadata
                metadata: Dict[str, Any] = {}

                # Tokens (if available)
                prompt_tokens = 0
                completion_tokens = 0
                if hasattr(response, "usage") and response.usage:
                    prompt_tokens = getattr(response.usage, "prompt_tokens", 0)
                    completion_tokens = getattr(response.usage, "completion_tokens", 0)
                    metadata["tokens"] = {
                        "prompt": prompt_tokens,
                        "completion": completion_tokens,
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

                # Record LLM call in metadata collector
                metadata_collector = get_metadata_collector()
                metadata_collector.record_llm_call(
                    model=model_str,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )

                # Set comprehensive span attributes per telemetry spec
                run_id = get_current_run_id()
                if run_id:
                    span.set_attribute("run_id", run_id)
                span.set_attribute("llm.provider", metadata["provider"])
                span.set_attribute("llm.model", metadata["model"])
                span.set_attribute("llm.tokens.prompt", prompt_tokens)
                span.set_attribute("llm.tokens.completion", completion_tokens)
                span.set_attribute("llm.tokens.total", metadata["tokens"]["total"])
                span.set_attribute("llm.latency_ms", duration_ms)

                return ProviderResult(output=output, metadata=metadata)

            except TimeoutError as e:
                raise ProcessorError(
                    "LLM call timed out - Increase timeout_seconds or check provider status"
                ) from e
            except Exception as e:
                raise ProcessorError(
                    f"LLM call failed: {e} - Check provider configuration and API key"
                ) from e
