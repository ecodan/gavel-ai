"""
Conversational processing step for multi-turn dialogue evaluation.

Responsibilities:
- Orchestrate multi-turn conversation execution across scenarios × variants
- Use TurnGenerator for dynamic user turn generation
- Execute conversations with deterministic user turns across variants
- Store conversation transcripts and results in context

Per TDD Conversational Evaluation: ConversationalProcessingStep is a Step,
following the same pattern as ScenarioProcessorStep for OneShot.
"""

import logging
import time
from datetime import UTC, datetime  # type: ignore[attr-defined]
from typing import Any, Dict, List, Optional

from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ConfigError, ProcessorError
from gavel_ai.core.steps.base import Step, StepPhase
from gavel_ai.models.agents import ModelDefinition
from gavel_ai.models.config import ConversationalConfig
from gavel_ai.models.conversation import (
    ConversationResult,
    ConversationScenario,
    ConversationState,
    TurnMetadata,
    TurnResult,
)
from gavel_ai.processors.turn_generator import TurnGenerator
from gavel_ai.providers.factory import ProviderFactory


class ConversationalProcessingStep(Step):
    """
    Multi-turn dialogue execution step.

    Orchestrates conversation execution for scenarios × variants,
    ensuring deterministic user turns across all variants of the same scenario.

    Per TDD Architecture:
    - Inherits from Step (not InputProcessor)
    - Reads config from RunContext
    - Writes results to RunContext
    - Follows same pattern as ScenarioProcessorStep
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialize ConversationalProcessingStep.

        Args:
            logger: Logger for step execution (class-level logging)
        """
        super().__init__(logger)
        self.provider_factory = ProviderFactory()

    @property
    def phase(self) -> StepPhase:
        """Return the workflow phase for this step."""
        return StepPhase.SCENARIO_PROCESSING

    async def execute(self, context: RunContext) -> None:
        """
        Execute conversational evaluation across scenarios × variants.

        Reads configuration from context, executes conversations,
        and stores results in context for downstream steps.

        Args:
            context: RunContext for reading configs and writing results

        Raises:
            ConfigError: If configuration is invalid
            ProcessorError: If conversation execution fails
        """
        # Read configuration from context
        eval_config = context.eval_context.eval_config.read()
        agents_config = context.eval_context.agents.read()

        # Validate workflow type
        if eval_config.workflow_type != "conversational":
            raise ConfigError(
                f"ConversationalProcessingStep requires workflow_type='conversational', "
                f"got '{eval_config.workflow_type}'"
            )

        # Get conversational config
        conv_config: ConversationalConfig = eval_config.conversational
        if conv_config is None:
            raise ConfigError(
                "Conversational config not found - Add 'conversational' section to eval_config.json"
            )

        # Get variants
        variants: List[str] = eval_config.variants
        if not variants:
            raise ConfigError("No variants configured in eval_config")

        # Load scenarios (as ConversationScenario)
        scenarios = self._load_conversation_scenarios(context)
        if not scenarios:
            raise ConfigError("No scenarios found for conversational evaluation")

        # Get turn generator model definition
        turn_gen_model_def = self._get_model_definition(
            agents_config, conv_config.turn_generator.model_id
        )

        # Get test subject model definition (first variant)
        # For conversational, we test each variant against the scenarios
        self.logger.info(
            f"Executing {len(scenarios)} scenarios × {len(variants)} variants "
            f"(max_turns={conv_config.max_turns})"
        )

        # Execute conversations
        all_results: List[ConversationResult] = []
        determinism_violations: List[Dict[str, Any]] = []

        for scenario in scenarios:
            # Create ONE TurnGenerator per scenario (shared across all variants)
            # This ensures deterministic user turns across variants (AC #2)
            turn_generator = TurnGenerator(
                scenario=scenario,
                model_def=turn_gen_model_def,
                max_turns=conv_config.max_turns,
            )

            scenario_results: List[ConversationResult] = []

            for variant_id in variants:
                # Get model definition for this variant
                variant_model_def = self._get_model_definition(agents_config, variant_id)

                # Execute conversation
                result = await self._execute_conversation(
                    scenario=scenario,
                    variant_id=variant_id,
                    model_def=variant_model_def,
                    turn_generator=turn_generator,
                    max_turns=conv_config.max_turns,
                )
                scenario_results.append(result)

            # Validate determinism across variants for this scenario
            violation = self._validate_determinism(scenario.scenario_id, scenario_results)
            if violation:
                determinism_violations.append(violation)

            all_results.extend(scenario_results)

        # Store results in context
        context.conversation_results = all_results
        context.determinism_violations = determinism_violations

        # Log summary
        successful = sum(1 for r in all_results if not r.error)
        failed = sum(1 for r in all_results if r.error)
        self.logger.info(
            f"Completed {len(all_results)} conversations: "
            f"{successful} successful, {failed} failed, "
            f"{len(determinism_violations)} determinism violations"
        )

        # Set test_subject and model_variant for downstream steps
        if eval_config.test_subjects:
            context.test_subject = eval_config.test_subjects[0].prompt_name or "conversational"
        else:
            context.test_subject = "conversational"
        context.model_variant = variants[0] if variants else "unknown"

    def _load_conversation_scenarios(self, context: RunContext) -> List[ConversationScenario]:
        """
        Load scenarios from context and convert to ConversationScenario.

        Args:
            context: RunContext with scenarios data source

        Returns:
            List of ConversationScenario objects
        """
        raw_scenarios = context.eval_context.scenarios.read()
        scenarios: List[ConversationScenario] = []

        for raw in raw_scenarios:
            # Handle both Scenario model and dict
            if hasattr(raw, "model_dump"):
                data = raw.model_dump()
            else:
                data = raw

            # Map fields: id/scenario_id → scenario_id, input → user_goal
            scenario_id = data.get("scenario_id") or data.get("id")
            user_goal = data.get("user_goal") or data.get("input")
            context_text = data.get("context")
            dialogue_guidance = data.get("dialogue_guidance")

            if not scenario_id or not user_goal:
                self.logger.warning("Skipping invalid scenario: missing scenario_id or user_goal")
                continue

            scenarios.append(
                ConversationScenario(
                    scenario_id=scenario_id,
                    user_goal=user_goal if isinstance(user_goal, str) else str(user_goal),
                    context=context_text,
                    dialogue_guidance=dialogue_guidance,
                )
            )

        return scenarios

    def _get_model_definition(self, agents_config: dict, model_id: str) -> ModelDefinition:
        """
        Get model definition from agents config.

        Args:
            agents_config: The agents configuration dict
            model_id: Model ID to look up (can be model name or agent name)

        Returns:
            ModelDefinition instance

        Raises:
            ConfigError: If model not found
        """
        models = agents_config.get("_models", {})

        # Check if it's a direct model name
        if model_id in models:
            return ModelDefinition.model_validate(models[model_id])

        # Check if it's an agent name that references a model
        if model_id in agents_config:
            agent = agents_config[model_id]
            referenced_model_id = agent.get("model_id")
            if referenced_model_id and referenced_model_id in models:
                return ModelDefinition.model_validate(models[referenced_model_id])

        raise ConfigError(
            f"Model '{model_id}' not found in _models or agents - "
            f"Add '{model_id}' to _models section of agents.json"
        )

    async def _execute_conversation(
        self,
        scenario: ConversationScenario,
        variant_id: str,
        model_def: ModelDefinition,
        turn_generator: TurnGenerator,
        max_turns: int,
    ) -> ConversationResult:
        """
        Execute a single conversation for given scenario and variant.

        Args:
            scenario: Conversation scenario to execute
            variant_id: Variant ID being tested
            model_def: Model definition for the test subject
            turn_generator: Shared TurnGenerator instance for this scenario
            max_turns: Maximum turns per conversation

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

        # Create agent for this variant
        agent = self.provider_factory.create_agent(model_def)

        results_raw: List[TurnResult] = []

        try:
            with self.tracer.start_as_current_span("conversation.execute") as span:
                span.set_attribute("scenario_id", scenario.scenario_id)
                span.set_attribute("variant_id", variant_id)
                span.set_attribute("max_turns", max_turns)

                # Generate initial user turn
                generated_turn = await turn_generator.generate_turn(scenario, conversation)
                # Ensure metadata is dict (may be None or empty dict)
                turn_gen_metadata = generated_turn.metadata or {}
                turn_metadata = TurnMetadata(
                    tokens_prompt=(turn_gen_metadata.get("tokens") or {}).get("prompt"),
                    tokens_completion=(turn_gen_metadata.get("tokens") or {}).get("completion"),
                    latency_ms=turn_gen_metadata.get("latency_ms"),
                    extra=turn_gen_metadata.get("extra"),
                )
                conversation.add_turn("user", generated_turn.content, turn_metadata)

                # Main conversation loop
                # Note: turn_count tracks LLM calls (assistant responses)
                # max_turns limits the number of LLM calls, not total turns
                # Total turns = 1 initial user turn + (turn_count * 2)
                turn_count = 0
                while generated_turn.should_continue and turn_count < max_turns:
                    turn_count += 1

                    # Call LLM (Test Subject) for assistant response
                    assistant_start = time.time()
                    result = await self.provider_factory.call_agent(
                        agent,
                        conversation.history,
                    )
                    assistant_response = result.output
                    assistant_latency = result.metadata.get(
                        "latency_ms", int((time.time() - assistant_start) * 1000)
                    )

                    # Extract token information
                    tokens_prompt = result.metadata.get("tokens", {}).get("prompt", 0)
                    tokens_completion = result.metadata.get("tokens", {}).get("completion", 0)

                    # Add assistant turn to transcript
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

                    # Create TurnResult for assistant's output
                    turn_result = TurnResult(
                        turn_number=len(conversation.turns) - 1,
                        processor_output=assistant_response,
                        latency_ms=assistant_latency,
                        tokens_prompt=tokens_prompt,
                        tokens_completion=tokens_completion,
                        error=None,
                    )
                    results_raw.append(turn_result)

                    # Generate next user turn
                    generated_turn = await turn_generator.generate_turn(scenario, conversation)

                    # Add user turn to transcript if continuing
                    if generated_turn.should_continue:
                        # Ensure metadata is dict (may be None or empty dict)
                        turn_gen_metadata = generated_turn.metadata or {}
                        turn_metadata = TurnMetadata(
                            tokens_prompt=(turn_gen_metadata.get("tokens") or {}).get("prompt"),
                            tokens_completion=(turn_gen_metadata.get("tokens") or {}).get(
                                "completion"
                            ),
                            latency_ms=turn_gen_metadata.get("latency_ms"),
                            extra=turn_gen_metadata.get("extra"),
                        )
                        conversation.add_turn("user", generated_turn.content, turn_metadata)

                # Finalize conversation result
                duration_ms = int((time.time() - start_time) * 1000)
                completed = not generated_turn.should_continue or turn_count >= max_turns

                # Compute total tokens
                tokens_total = sum(
                    (r.tokens_prompt or 0) + (r.tokens_completion or 0) for r in results_raw
                )

                span.set_attribute("total_turns", len(conversation.turns))
                span.set_attribute("completed", completed)
                span.set_attribute("tokens_total", tokens_total)

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

        except (ProcessorError, ConfigError) as e:
            # Expected errors (LLM failures, config issues)
            duration_ms = int((time.time() - start_time) * 1000)
            self.logger.error(
                f"Conversation failed for scenario={scenario.scenario_id} "
                f"variant={variant_id}: {type(e).__name__}: {e}"
            )
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
        except Exception as e:
            # Unexpected errors (programming bugs, unexpected exceptions)
            duration_ms = int((time.time() - start_time) * 1000)
            self.logger.exception(
                f"UNEXPECTED ERROR in conversation: "
                f"scenario={scenario.scenario_id} variant={variant_id}"
            )
            return ConversationResult(
                scenario_id=scenario.scenario_id,
                variant_id=variant_id,
                conversation_transcript=conversation,
                results_raw=results_raw,
                duration_ms=duration_ms,
                completed=False,
                tokens_total=0,
                error=f"Unexpected error: {type(e).__name__}: {e}",
                timestamp=datetime.now(UTC),
            )

    def _validate_determinism(
        self, scenario_id: str, results: List[ConversationResult]
    ) -> Optional[Dict[str, Any]]:
        """
        Validate that user turns are identical across variants of the same scenario.

        This is a critical validation for AC #2 - identical user turns across variants.

        Args:
            scenario_id: ID of the scenario being validated
            results: List of conversation results for this scenario (one per variant)

        Returns:
            Dict describing violation if found, None otherwise
        """
        if len(results) < 2:
            return None

        # Extract user turns from first conversation as baseline
        baseline = results[0]
        baseline_user_turns = [
            turn.content for turn in baseline.conversation_transcript.turns if turn.role == "user"
        ]

        # Compare with other variants
        for result in results[1:]:
            user_turns = [
                turn.content for turn in result.conversation_transcript.turns if turn.role == "user"
            ]

            if user_turns != baseline_user_turns:
                return {
                    "scenario_id": scenario_id,
                    "baseline_variant": baseline.variant_id,
                    "variant_id": result.variant_id,
                    "baseline_user_turns": baseline_user_turns,
                    "variant_user_turns": user_turns,
                }

        return None
