"""
ConversationalProcessingStep for multi-turn conversation orchestration.

.. deprecated::
    This InputProcessor-based implementation is deprecated.
    Use :class:`gavel_ai.core.steps.ConversationalProcessingStep` instead,
    which follows the proper Step abstraction pattern consistent with
    the OneShot workflow architecture.

    The Step-based version:
    - Inherits from Step (not InputProcessor)
    - Reads configuration from RunContext
    - Writes results to RunContext
    - Integrates with ValidatorStep, JudgeRunnerStep, ReportRunnerStep

ConversationalProcessingStep is core orchestrator for multi-turn dialogues.
It manages scenario × variant execution with complete transcript generation.
"""

import time
import warnings
from datetime import UTC, datetime  # type: ignore[attr-defined]
from typing import Any, Dict, List

from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.models.agents import ModelDefinition
from gavel_ai.models.conversation import (
    ConversationResult,
    ConversationScenario,
    ConversationState,
    TurnMetadata,
    TurnResult,
)
from gavel_ai.models.runtime import Input, ProcessorConfig, ProcessorResult
from gavel_ai.processors.base import InputProcessor
from gavel_ai.processors.turn_generator import TurnGenerator
from gavel_ai.providers.factory import ProviderFactory
from gavel_ai.telemetry import get_tracer


class ConversationalProcessingStep(InputProcessor):
    """
    Processor for multi-turn conversation orchestration.

    .. deprecated::
        Use :class:`gavel_ai.core.steps.ConversationalProcessingStep` instead.

    Manages scenario × variant execution with complete transcript generation.
    Follows these patterns:
    - Sequential turns within conversations
    - Parallel scenario × variant execution
    - Two-artifact design: conversations.jsonl + results_raw.jsonl
    """

    def __init__(
        self,
        config: ProcessorConfig,
        scenarios: List[ConversationScenario],
        variants: List[str],
        model_def: ModelDefinition,
        max_turns: int = 10,
    ):
        """
        Initialize ConversationalProcessingStep.

        .. deprecated::
            Use :class:`gavel_ai.core.steps.ConversationalProcessingStep` instead.

        Args:
            config: Processor configuration
            scenarios: List of conversation scenarios
            variants: List of variant IDs to test
            model_def: Model definition for LLM calls
            max_turns: Maximum turns per conversation (default: 10)

        Raises:
            ValueError: If scenarios or variants are empty
        """
        warnings.warn(
            "gavel_ai.processors.ConversationalProcessingStep is deprecated. "
            "Use gavel_ai.core.steps.ConversationalProcessingStep instead, "
            "which follows the proper Step abstraction pattern.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(config)
        self.tracer = get_tracer(__name__)

        if not scenarios:
            raise ValueError("scenarios cannot be empty")
        if not variants:
            raise ValueError("variants cannot be empty")

        self.scenarios = scenarios
        self.variants = variants
        self.model_def = model_def
        self.max_turns = max_turns

        # Provider factory for creating agents
        self.provider_factory = ProviderFactory()

        # Create agent from model definition
        self.agent = self.provider_factory.create_agent(model_def)

    def _validate_determinism_across_variants(
        self, results: List[ConversationResult], span
    ) -> None:
        """
        Validate that user turns are identical across variants of the same scenario.

        This is a critical validation for AC #2 - identical user turns across variants.
        If differences are detected, a warning is logged but execution continues.

        Args:
            results: List of conversation results to validate
            span: Telemetry span for recording validation events
        """
        # Group results by scenario_id
        scenario_results = {}
        for result in results:
            if result.scenario_id not in scenario_results:
                scenario_results[result.scenario_id] = []
            scenario_results[result.scenario_id].append(result)

        # Check each scenario for user turn consistency
        for scenario_id, scenario_conversations in scenario_results.items():
            if len(scenario_conversations) < 2:
                # No multiple variants to compare
                continue

            # Extract user turns from first conversation as baseline
            baseline_conv = scenario_conversations[0]
            baseline_user_turns = [
                turn.content
                for turn in baseline_conv.conversation_transcript.turns
                if turn.role == "user"
            ]

            # Compare with other variants
            for conv in scenario_conversations[1:]:
                user_turns = [
                    turn.content
                    for turn in conv.conversation_transcript.turns
                    if turn.role == "user"
                ]

                if user_turns != baseline_user_turns:
                    span.add_event(
                        "determinism_violation",
                        {
                            "scenario_id": scenario_id,
                            "baseline_variant": baseline_conv.variant_id,
                            "variant_id": conv.variant_id,
                            "baseline_user_turns": baseline_user_turns,
                            "variant_user_turns": user_turns,
                        },
                    )
                    span.set_attribute("determinism_validation", "FAILED")
                    return

        span.set_attribute("determinism_validation", "PASSED")

    async def _execute_conversation(
        self, scenario: ConversationScenario, variant_id: str, turn_generator: TurnGenerator
    ) -> ConversationResult:
        """
        Execute a single conversation for given scenario and variant.

        Args:
            scenario: Conversation scenario to execute
            variant_id: Variant ID being tested
            turn_generator: Shared TurnGenerator instance for this scenario (ensures deterministic user turns across variants)

        Returns:
            ConversationResult with full transcript and turn results
        """
        start_time = time.time()

        # Create conversation state
        conversation = ConversationState(
            scenario_id=scenario.scenario_id,
            variant_id=variant_id,
            metadata=None,
        )

        # Use provided turn_generator (shared across all variants of this scenario)
        results_raw: List[TurnResult] = []

        try:
            # Generate initial user turn
            generated_turn = await turn_generator.generate_turn(scenario, conversation)
            turn_metadata = TurnMetadata(
                tokens_prompt=generated_turn.metadata.get("tokens", {}).get("prompt"),
                tokens_completion=generated_turn.metadata.get("tokens", {}).get("completion"),
                latency_ms=generated_turn.metadata.get("latency_ms"),
                extra=generated_turn.metadata.get("extra"),
            )
            conversation.add_turn("user", generated_turn.content, turn_metadata)

            # Main conversation loop
            # Loop continues as long as turn_generator says so AND we haven't hit the turn limit
            # Note: TurnGenerator already checks max_turns, but we keep a safety check here.
            while generated_turn.should_continue and len(conversation.turns) < 2 * self.max_turns:
                # 1. Call LLM (Test Subject) for assistant response
                assistant_start = time.time()
                # Pass full history string to agent
                result = await self.provider_factory.call_agent(
                    self.agent,
                    conversation.history,
                )
                assistant_response = result.output
                assistant_latency = result.metadata.get(
                    "latency_ms", int((time.time() - assistant_start) * 1000)
                )

                # Extract token information
                tokens_prompt = result.metadata.get("tokens", {}).get("prompt", 0)
                tokens_completion = result.metadata.get("tokens", {}).get("completion", 0)

                # 2. Add assistant turn to transcript
                conversation.add_turn(
                    "assistant",
                    assistant_response,
                    TurnMetadata(
                        latency_ms=assistant_latency,
                        tokens_prompt=tokens_prompt,
                        tokens_completion=tokens_completion,
                        extra=None,
                    ),
                )

                # 3. Create TurnResult for assistant's output
                turn_result = TurnResult(
                    turn_number=len(conversation.turns) - 1,
                    processor_output=assistant_response,
                    latency_ms=assistant_latency,
                    tokens_prompt=tokens_prompt,
                    tokens_completion=tokens_completion,
                    error=None,
                )
                results_raw.append(turn_result)

                # 4. Generate next user turn
                generated_turn = await turn_generator.generate_turn(scenario, conversation)

                # Add user turn to transcript
                turn_metadata = TurnMetadata(
                    tokens_prompt=generated_turn.metadata.get("tokens", {}).get("prompt"),
                    tokens_completion=generated_turn.metadata.get("tokens", {}).get("completion"),
                    latency_ms=generated_turn.metadata.get("latency_ms"),
                    extra=generated_turn.metadata.get("extra"),
                )
                conversation.add_turn("user", generated_turn.content, turn_metadata)

            # Finalize conversation result
            duration_ms = int((time.time() - start_time) * 1000)
            completed = (
                not generated_turn.should_continue or len(conversation.turns) >= 2 * self.max_turns
            )

            # Compute total tokens
            tokens_total = sum(
                (r.tokens_prompt or 0) + (r.tokens_completion or 0) for r in results_raw
            )

            return ConversationResult(
                scenario_id=scenario.scenario_id,
                variant_id=variant_id,
                conversation_transcript=conversation,
                results_raw=results_raw,
                duration_ms=duration_ms,
                completed=completed,
                tokens_total=tokens_total,
                error=None,
                timestamp=datetime.now(UTC),
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ConversationResult(
                scenario_id=scenario.scenario_id,
                variant_id=variant_id,
                conversation_transcript=conversation,
                results_raw=results_raw,
                duration_ms=duration_ms,
                completed=False,
                tokens_total=0,
                error=str(e),
                timestamp=datetime.now(UTC),
            )

    async def process(self, inputs: List[Input]) -> ProcessorResult:  # noqa: C901
        """
        Execute processor against batch of inputs.

        Args:
            inputs: List of Input instances to process.
                   Each input id should correspond to a scenario_id in self.scenarios.

        Returns:
            ProcessorResult with aggregated conversation results in metadata.

        Raises:
            ProcessorError: On execution failures
        """
        if not inputs:
            raise ProcessorError("inputs cannot be empty")

        with self.tracer.start_as_current_span("conversational.execute") as span:
            span.set_attribute("input_count", len(inputs))
            span.set_attribute("variant_count", len(self.variants))
            span.set_attribute("max_turns", self.max_turns)

            # Map inputs to scenarios we have
            scenario_map = {s.scenario_id: s for s in self.scenarios}

            # Execute conversations for each input scenario × each variant
            # CRITICAL: Create ONE TurnGenerator per scenario and share it across all variants
            # This ensures deterministic user turns across variants (AC #2)
            # FIXED: Use safer execution to avoid race conditions with shared TurnGenerator
            all_conversations = []
            for input_item in inputs:
                scenario = scenario_map.get(input_item.id)
                if not scenario:
                    # If scenario not found in self.scenarios, we could either error or skip.
                    # Given current architecture, it SHOULD be there.
                    span.add_event("scenario_not_found", {"scenario_id": input_item.id})
                    continue

                # Create ONE TurnGenerator for this scenario (shared across all variants)
                turn_generator = TurnGenerator(scenario, self.model_def, self.max_turns)

                # Execute variants sequentially for this scenario to avoid race conditions
                # Then wait for all scenarios to complete in parallel
                variant_conversations = []
                for variant_id in self.variants:
                    try:
                        conversation = await self._execute_conversation(
                            scenario, variant_id, turn_generator
                        )
                        variant_conversations.append(conversation)
                    except Exception as e:
                        if self.config.error_handling == "fail_fast":
                            raise ProcessorError(f"Conversation execution failed: {e}") from e
                        else:
                            # Convert exception to error result for continued execution
                            error_conversation = ConversationResult(
                                scenario_id=scenario.scenario_id,
                                variant_id=variant_id,
                                conversation_transcript=ConversationState(
                                    scenario_id=scenario.scenario_id,
                                    variant_id=variant_id,
                                    metadata=None,
                                ),
                                results_raw=[],
                                duration_ms=0,
                                completed=False,
                                tokens_total=0,
                                error=str(e),
                                timestamp=datetime.now(UTC),
                            )
                            variant_conversations.append(error_conversation)

                all_conversations.extend(variant_conversations)

            if not all_conversations:
                return ProcessorResult(output="No conversations to execute", metadata={})

            # Handle results and exceptions
            results: List[ConversationResult] = []
            errors: List[str] = []
            for conversation in all_conversations:
                if conversation.error:
                    errors.append(
                        f"Scenario {conversation.scenario_id} variant {conversation.variant_id} failed: {conversation.error}"
                    )
                else:
                    results.append(conversation)

            # VALIDATION: Verify determinism of user turns across variants (AC #2)
            self._validate_determinism_across_variants(results, span)

            # Prepare metadata
            metadata: Dict[str, Any] = {
                "conversations": results,  # Full ConversationResult objects
                "total_conversations": len(results),
                "total_errors": len(errors),
            }

            if errors:
                metadata["errors"] = errors

            # Summarize results in output string
            output = (
                f"Executed {len(results)} conversations for {len(inputs)} scenarios across {len(self.variants)} variants. "
                f"Total errors: {len(errors)}"
            )

            return ProcessorResult(
                output=output,
                metadata=metadata,
                error="\n".join(errors) if errors else None,
            )
