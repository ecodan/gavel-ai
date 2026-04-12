"""
PromptInputProcessor implementation for local prompt evaluation.

Phase 3: Simplified to accept PromptInput with pre-rendered prompts.
Processes prompts against scenarios using Pydantic-AI provider abstraction.
"""

import asyncio
from typing import Any, Dict, List

from pydantic_ai import Agent

from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.core.retry import RetryConfig, retry_with_backoff
from gavel_ai.models.agents import ModelDefinition
from gavel_ai.models.runtime import ProcessorConfig, ProcessorResult, PromptInput
from gavel_ai.processors.base import InputProcessor
from gavel_ai.providers.factory import ProviderFactory
from gavel_ai.telemetry import get_tracer


class PromptInputProcessor(InputProcessor):
    """
    Process prompts against input scenarios using LLM providers.

    Per Architecture Decision 1: Uses Pydantic-AI v1.39.0 for provider abstraction.
    Per Architecture Decision 3: Config-driven design with per-processor batching.
    Per Architecture Decision 9: Emits OpenTelemetry spans immediately.
    """

    def __init__(self, config: ProcessorConfig, model_def: ModelDefinition):
        """
        Initialize processor with configuration.

        Args:
            config: ProcessorConfig instance with processor behavioral rules
            model_def: ModelDefinition for Pydantic-AI integration (required)
        """
        super().__init__(config)
        self.tracer = get_tracer(__name__)

        # Provider factory for creating agents
        self.provider_factory = ProviderFactory()

        # Create agent from model definition
        self.model_def = model_def
        self.agent: Agent = self.provider_factory.create_agent(model_def)

    async def _call_llm(self, messages: List[Dict[str, str]]) -> tuple[str, Dict[str, Any]]:
        """
        Call LLM with structured messages and return response with metadata.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
                     [{"role": "system|user|assistant", "content": "..."}]

        Returns:
            Tuple of (response_text, metadata_dict)

        Raises:
            ProcessorError: On LLM call failures
        """
        try:
            # Extract user message (combined with system prompt if present)
            user_content = next(
                (msg["content"] for msg in messages if msg.get("role") == "user"),
                ""
            )
            result = await self.provider_factory.call_agent(self.agent, user_content)
            return (result.output, result.metadata)
        except ProcessorError:
            raise
        except Exception as e:
            raise ProcessorError(
                f"Unexpected error during LLM call: {e} - Check logs for details"
            ) from e

    async def process(self, inputs: List[PromptInput]) -> ProcessorResult:
        """
        Execute processor against batch of PromptInput instances.

        Phase 3: Accepts PromptInput with pre-rendered prompts (from ScenarioProcessorStep).
        Constructs messages from user/system prompts and calls LLM.

        Args:
            inputs: List of PromptInput instances with rendered prompts

        Returns:
            ProcessorResult with output, metadata, and optional error

        Raises:
            ProcessorError: On execution failures
        """
        all_outputs: List[str] = []
        aggregated_metadata: Dict[str, Any] = {
            "total_tokens": 0,
            "total_latency_ms": 0,
            "input_count": len(inputs),
        }
        last_metadata: Dict[str, Any] = {}

        for input_item in inputs:
            # Construct messages from PromptInput
            messages: List[Dict[str, str]] = []
            if input_item.system:
                messages.append({"role": "system", "content": input_item.system})
            messages.append({"role": "user", "content": input_item.user})

            # Call LLM with retry logic
            retry_config = RetryConfig(max_retries=3)

            async def call_llm_attempt() -> tuple[str, Dict[str, Any]]:
                return await self._call_llm(messages)

            try:
                output, metadata = await retry_with_backoff(
                    func=call_llm_attempt,
                    retry_config=retry_config,
                    transient_exceptions=(TimeoutError,),
                    error_message_template="LLM call timed out after {max_retries} retries - Increase timeout_seconds in config or check provider status",
                )

                all_outputs.append(output)
                last_metadata = metadata

                # Aggregate metadata
                if "tokens" in metadata and isinstance(metadata["tokens"], dict):
                    aggregated_metadata["total_tokens"] += metadata["tokens"].get("total", 0)
                if "latency_ms" in metadata:
                    aggregated_metadata["total_latency_ms"] += metadata["latency_ms"]

            except ProcessorError:
                raise
            except Exception as e:
                raise ProcessorError(
                    f"Failed to process input {input_item.id}: {e} - "
                    f"Check input format and LLM configuration"
                ) from e

        # Preserve detailed metadata from last response
        if last_metadata:
            aggregated_metadata.update(
                {
                    k: v
                    for k, v in last_metadata.items()
                    if k not in ["latency_ms"] and not k.startswith("total_")
                }
            )

        # Combine all outputs
        combined_output = "\n\n".join(all_outputs) if len(all_outputs) > 1 else all_outputs[0]

        return ProcessorResult(
            output=combined_output,
            metadata=aggregated_metadata,
        )
