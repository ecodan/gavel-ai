"""
PromptInputProcessor implementation for local prompt evaluation.

Processes prompts against scenarios using Pydantic-AI provider abstraction.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from pydantic_ai import Agent

from gavel_ai.core.config.agents import ModelDefinition
from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.core.models import Input, ProcessorConfig, ProcessorResult
from gavel_ai.processors.base import InputProcessor
from gavel_ai.providers.factory import ProviderFactory
from gavel_ai.telemetry import get_current_run_id, get_tracer


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

    def _render_prompt(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Render prompt template with scenario variables.

        Args:
            template: Prompt template string with {variable} placeholders
            variables: Dictionary of variable values to substitute

        Returns:
            Rendered prompt string

        Raises:
            ProcessorError: If required variables are missing from scenario
        """
        try:
            rendered = template.format(**variables)
            return rendered
        except KeyError as e:
            missing_var = e.args[0]
            raise ProcessorError(
                f"Missing required variable '{missing_var}' in scenario input - "
                f"Add '{missing_var}' to scenario data or update template"
            ) from e

    async def _call_llm(self, prompt: str) -> tuple[str, Dict[str, Any]]:
        """
        Call LLM with prompt and return response with metadata.

        Args:
            prompt: Rendered prompt text

        Returns:
            Tuple of (response_text, metadata_dict)

        Raises:
            ProcessorError: On LLM call failures
        """
        try:
            result = await self.provider_factory.call_agent(self.agent, prompt)
            return (result.output, result.metadata)
        except ProcessorError:
            raise
        except Exception as e:
            raise ProcessorError(
                f"Unexpected error during LLM call: {e} - Check logs for details"
            ) from e

    async def process(self, inputs: List[Input]) -> ProcessorResult:
        """
        Execute processor against batch of inputs.

        Args:
            inputs: List of Input instances to process

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
            # For now, use the input text directly as the prompt
            # Real implementation will load template and render with variables
            prompt = input_item.text

            # Call LLM with retry logic
            max_retries = 3

            for attempt in range(max_retries + 1):
                try:
                    output, metadata = await self._call_llm(prompt)
                    all_outputs.append(output)
                    last_metadata = metadata

                    # Aggregate metadata
                    if "tokens" in metadata and isinstance(metadata["tokens"], dict):
                        aggregated_metadata["total_tokens"] += metadata["tokens"].get("total", 0)
                    if "latency_ms" in metadata:
                        aggregated_metadata["total_latency_ms"] += metadata["latency_ms"]

                    # Success - break retry loop
                    break

                except TimeoutError as e:
                    if attempt < max_retries:
                        # Exponential backoff
                        delay = min(1.0 * (2**attempt), 30.0)
                        await asyncio.sleep(delay)
                    else:
                        raise ProcessorError(
                            f"LLM call timed out after {max_retries} retries - "
                            f"Increase timeout_seconds in config or check provider status"
                        ) from e
                except ProcessorError:
                    # Re-raise ProcessorError as-is
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
