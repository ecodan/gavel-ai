"""
TurnGenerator component for dynamic conversational turn generation.

TurnGenerator is core innovation for conversational evaluation - it generates
user turns ON-THE-FLY, not pre-written, based on scenario context and conversation history.

Performance requirement: Turn generation must complete in <1s per NFR-C-P1.
Determinism requirement: Identical inputs with temperature=0 produce identical turns per NFR-C-R4.
"""

import time
from typing import Any, Dict

from pydantic import BaseModel, Field

from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.models.agents import ModelDefinition
from gavel_ai.models.conversation import ConversationScenario, ConversationState
from gavel_ai.providers.factory import ProviderFactory
from gavel_ai.telemetry import get_tracer


class GeneratedTurn(BaseModel):
    """Data structure for a generated turn in conversation.

    Contains turn content, metadata, and continuation flag.
    """

    content: str = Field(..., description="Content of generated turn")
    metadata: Dict[str, Any] = Field(..., description="Metadata about turn generation")
    should_continue: bool = Field(..., description="Whether conversation should continue")


class TurnGenerator:
    """
    Component that creates turns dynamically for conversational evaluation.

    TurnGenerator uses LLM models to generate realistic user responses that
    move toward scenario's user_goal while respecting dialogue guidance.

    Key features:
    - On-the-fly turn generation (not pre-written)
    - Goal-directed conversation flow
    - Deterministic behavior with temperature=0
    - Performance: <1s per turn (NFR-C-P1)
    """

    def __init__(
        self,
        scenario: ConversationScenario,
        model_def: ModelDefinition,
        max_turns: int = 10,
    ):
        """
        Initialize TurnGenerator with scenario and model definition.

        Args:
            scenario: The conversational scenario to generate turns for
            model_def: Model definition for LLM configuration
            max_turns: Maximum number of conversation turns allowed (default: 10)

        Raises:
            ValueError: If scenario or model_def is invalid
        """
        self._validate_inputs(scenario, model_def)

        self.scenario = scenario
        self.model_def = model_def
        self._max_turns = max_turns
        self.tracer = get_tracer(__name__)
        self.provider_factory = ProviderFactory()

        try:
            self.agent = self.provider_factory.create_agent(model_def)
        except Exception as e:
            raise ProcessorError(
                f"Failed to create LLM agent for turn generation: {e} - "
                f"Check provider configuration and API key in model_def"
            ) from e

        # Goal achievement indicators
        self._goal_achievement_indicators = [
            "thank you",
            "thanks",
            "great",
            "perfect",
            "excellent",
            "wonderful",
            "worked",
            "success",
            "resolved",
            "fixed",
            "solved",
            "accomplished",
            "no further help",
            "that is all",
        ]
        self._negation_words = ["not", "never", "haven't", "hasn't", "doesn't", "don't", "won't"]

    def _is_deterministic_mode(self) -> bool:
        """Check if model is configured for deterministic behavior."""
        return self.model_def.model_parameters.get("temperature", 0.7) == 0.0

    def _validate_inputs(self, scenario: ConversationScenario, model_def: ModelDefinition) -> None:
        """Validate constructor inputs.

        Args:
            scenario: The conversational scenario to validate
            model_def: The model definition to validate

        Raises:
            ValueError: If inputs are invalid
        """
        if not scenario.user_goal or not scenario.user_goal.strip():
            raise ValueError("Scenario must have a non-empty user_goal")

        if not model_def.model_provider or not model_def.model_family:
            raise ValueError("Model definition must specify provider and family")

    async def generate_turn(
        self, scenario: ConversationScenario, history: ConversationState
    ) -> GeneratedTurn:
        """
        Generate next turn in a conversation.

        Args:
            scenario: The conversational scenario
            history: Current conversation state with turn history

        Returns:
            GeneratedTurn with content, metadata, and should_continue flag

        Raises:
            Exception: If LLM call fails or validation errors occur
        """
        start_time = time.time()

        try:
            with self.tracer.start_as_current_span("generate_turn") as span:
                span.set_attribute("scenario_id", scenario.scenario_id)
                span.set_attribute("total_turns", len(history.turns))
                span.set_attribute(
                    "model_temperature",
                    self.model_def.model_parameters.get("temperature", "default"),
                )
                span.set_attribute("deterministic_mode", self._is_deterministic_mode())

                # Build prompt for LLM with deterministic ordering
                prompt = self._build_turn_prompt(scenario, history)
                span.set_attribute("prompt_length", len(prompt))
                span.set_attribute("prompt_hash", hash(prompt))  # For determinism verification

                # Call LLM normally
                result = await self.provider_factory.call_agent(self.agent, prompt)
                content = result.output
                metadata = result.metadata

                # Determine if conversation should continue
                should_continue = self._should_continue(scenario, history, content)
                span.set_attribute("should_continue", should_continue)
                span.set_attribute("goal_achieved", not should_continue)

                # Performance tracking
                generation_time = time.time() - start_time
                span.set_attribute("generation_time_ms", int(generation_time * 1000))

                # Performance requirement check (NFR-C-P1)
                if generation_time >= 1.0:
                    span.add_event(
                        "performance_warning",
                        {
                            "warning": "turn_generation_exceeded_1s",
                            "generation_time_s": generation_time,
                            "requirement": "<1s per NFR-C-P1",
                        },
                    )

                return GeneratedTurn(
                    content=content,
                    metadata=metadata,
                    should_continue=should_continue,  # type: ignore
                )

        except Exception as e:
            with self.tracer.start_as_current_span("generate_turn_error") as span:
                span.record_exception(e)
                span.set_attribute("error_type", type(e).__name__)
                span.set_attribute("generation_time_ms", int((time.time() - start_time) * 1000))
                raise

    def _build_turn_prompt(self, scenario: ConversationScenario, history: ConversationState) -> str:
        """
        Build prompt for turn generation.

        Args:
            scenario: The conversational scenario
            history: Current conversation state

        Returns:
            Formatted prompt string designed for realistic user simulation
        """
        prompt_parts = [
            "You are simulating a user in a conversation. Generate next user response.",
            "",
            "SCENARIO:",
            f"User Goal: {scenario.user_goal}",
        ]

        if scenario.context:
            prompt_parts.append(f"Context: {scenario.context}")

        if scenario.dialogue_guidance:
            dg = scenario.dialogue_guidance
            if dg.tone_preference:
                prompt_parts.append(f"Tone: {dg.tone_preference}")
            if dg.escalation_strategy:
                prompt_parts.append(f"Escalation: {dg.escalation_strategy}")
            if dg.factual_constraints:
                constraints = ", ".join(dg.factual_constraints)
                prompt_parts.append(f"Facts you know: {constraints}")

        prompt_parts.extend(
            [
                "",
                "CONVERSATION HISTORY:",
                history.history if history.history else "(No previous turns)",
                "",
                "Generate next user response. Be concise and realistic. Do not include quotation marks or role labels.",
            ]
        )

        return "\n".join(prompt_parts)

    def _should_continue(
        self, scenario: ConversationScenario, history: ConversationState, generated_content: str
    ) -> bool:
        """
        Determine if conversation should continue based on goal achievement and limits.

        Uses simple heuristics for goal achievement detection. In production,
        this could be enhanced with more sophisticated NLP or LLM-based detection.

        Args:
            scenario: The conversational scenario
            history: Current conversation state
            generated_content: The content that was just generated

        Returns:
            True if conversation should continue, False otherwise
        """
        content_lower = generated_content.lower()

        # Check for goal achievement indicators with basic negation avoidance
        goal_achieved = False
        for indicator in self._goal_achievement_indicators:
            if indicator in content_lower:
                # Basic check for nearby negation words
                # Strip punctuation for more robust word matching
                words = [w.strip(".,!?;:") for w in content_lower.split()]
                try:
                    # Find index of first word of indicator
                    indicator_first_word = indicator.split()[0]
                    if indicator_first_word in words:
                        idx = words.index(indicator_first_word)
                        # Check preceding 2 words for negation
                        window = words[max(0, idx - 2) : idx]
                        if not any(neg in window for neg in self._negation_words):
                            goal_achieved = True
                            break
                    else:
                        # Fallback if substring but not whole word matched
                        goal_achieved = True
                        break
                except (ValueError, IndexError):
                    goal_achieved = True
                    break

        # Check turn limit
        max_reached = len(history.turns) >= self._max_turns

        # Continue if goal not achieved and max turns not reached
        return not goal_achieved and not max_reached
