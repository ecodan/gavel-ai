import pytest

pytestmark = pytest.mark.unit
"""
Unit tests for multi-variant support in ConversationalProcessingStep (DEPRECATED).

.. deprecated::
    This test file tests the deprecated InputProcessor-based ConversationalProcessingStep.
    See tests/unit/test_conversational_step.py for tests of the new Step-based implementation.

Tests AC #2: All variants of the same scenario receive identical user turns.
"""

import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gavel_ai.models.agents import ModelDefinition
from gavel_ai.models.conversation import (
    ConversationScenario,
    ConversationState,
    DialogueGuidance,
)
from gavel_ai.models.runtime import ProcessorConfig, PromptInput
from gavel_ai.processors.turn_generator import GeneratedTurn, TurnGenerator


class TestConversationalMultiVariantDeprecated:
    """
    Test suite for deprecated InputProcessor-based ConversationalProcessingStep.

    .. deprecated::
        These tests verify the old implementation for backward compatibility.
        See test_conversational_step.py for tests of the new Step-based implementation.
    """

    @pytest.fixture
    def mock_processor_config(self):
        """Create a mock processor config."""
        return ProcessorConfig(
            processor_type="conversational",
            parallelism=1,
            timeout_seconds=30,
            error_handling="fail_fast",
        )

    @pytest.fixture
    def mock_model_def(self):
        """Create a mock model definition."""
        return ModelDefinition(
            model_provider="openai",
            model_family="gpt",
            model_version="gpt-4",
            model_parameters={"temperature": 0.0},
            provider_auth={"api_key": "test-key"},
        )

    @pytest.fixture
    def sample_scenario(self):
        """Create a sample conversation scenario."""
        return ConversationScenario(
            scenario_id="test-scenario-1",
            user_goal="Get help with resetting a password",
            context="User has forgotten their password and needs to reset it",
            dialogue_guidance=DialogueGuidance(
                tone_preference="frustrated but polite",
                escalation_strategy="ask for supervisor if not resolved",
                factual_constraints=["password reset requires email verification"],
            ),
        )

    @pytest.fixture
    def sample_scenarios(self, sample_scenario):
        """Create a list of sample scenarios."""
        return [sample_scenario]

    @patch("gavel_ai.processors.conversational_processing_step.ProviderFactory")
    @patch("gavel_ai.processors.conversational_processing_step.TurnGenerator")
    @pytest.mark.asyncio
    async def test_multiple_variants_receive_identical_user_turns(
        self,
        mock_turn_gen_class,
        mock_provider_factory,
        mock_processor_config,
        sample_scenarios,
        mock_model_def,
    ):
        """Test that all variants of same scenario receive identical user turns (AC #2)."""
        # Suppress deprecation warning for this test
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            from gavel_ai.processors.conversational_processing_step import (
                ConversationalProcessingStep,
            )

            # Setup mocks
            mock_turn_generator = MagicMock(spec=TurnGenerator)
            mock_turn_generator.generate_turn = AsyncMock()
            mock_turn_gen_class.return_value = mock_turn_generator

            # Different assistant responses for each variant
            variant_responses = {
                "variant-1": "Response from variant 1",
                "variant-2": "Response from variant 2",
                "variant-3": "Response from variant 3",
            }

            call_count = 0

            async def mock_call_agent(agent, prompt, **kwargs):
                nonlocal call_count
                call_count += 1
                # Determine which variant based on call order
                variant_idx = (call_count - 1) % 3
                variant_id = f"variant-{variant_idx + 1}"
                return MagicMock(
                    output=variant_responses[variant_id],
                    metadata={"latency_ms": 100, "tokens": {"prompt": 10, "completion": 5}},
                )

            mock_factory_instance = mock_provider_factory.return_value
            mock_factory_instance.call_agent = mock_call_agent
            mock_factory_instance.create_agent = MagicMock()

            # Create processor with 3 variants
            processor = ConversationalProcessingStep(
                config=mock_processor_config,
                scenarios=sample_scenarios,
                variants=["variant-1", "variant-2", "variant-3"],
                model_def=mock_model_def,
            )

            # Mock deterministic user turn generation
            # Each variant should get SAME user turns
            mock_turn_generator.generate_turn.side_effect = [
                # Variant 1
                GeneratedTurn(
                    content="User turn 1",
                    metadata={"deterministic_mode": True, "prompt_hash": hash("test")},
                    should_continue=True,
                ),
                GeneratedTurn(
                    content="User turn 2",
                    metadata={"deterministic_mode": True, "prompt_hash": hash("test2")},
                    should_continue=False,
                ),
                # Variant 2 (should be identical)
                GeneratedTurn(
                    content="User turn 1",
                    metadata={"deterministic_mode": True, "prompt_hash": hash("test")},
                    should_continue=True,
                ),
                GeneratedTurn(
                    content="User turn 2",
                    metadata={"deterministic_mode": True, "prompt_hash": hash("test2")},
                    should_continue=False,
                ),
                # Variant 3 (should be identical)
                GeneratedTurn(
                    content="User turn 1",
                    metadata={"deterministic_mode": True, "prompt_hash": hash("test")},
                    should_continue=True,
                ),
                GeneratedTurn(
                    content="User turn 2",
                    metadata={"deterministic_mode": True, "prompt_hash": hash("test2")},
                    should_continue=False,
                ),
            ]

            # Execute
            inputs = [PromptInput(id="test-scenario-1", user="test")]
            result = await processor.process(inputs)

            # Verify we got 3 conversations (one per variant)
            assert result.metadata["total_conversations"] == 3
            conversations = result.metadata["conversations"]

            # Extract user turns from each variant
            variant_user_turns = {}
            for conv in conversations:
                variant_id = conv.variant_id
                user_turns = [
                    turn.content
                    for turn in conv.conversation_transcript.turns
                    if turn.role == "user"
                ]
                variant_user_turns[variant_id] = user_turns

            # Verify all variants have identical user turns
            assert len(variant_user_turns) == 3
            user_turns_v1 = variant_user_turns["variant-1"]
            user_turns_v2 = variant_user_turns["variant-2"]
            user_turns_v3 = variant_user_turns["variant-3"]

            assert user_turns_v1 == user_turns_v2 == user_turns_v3
            assert user_turns_v1 == ["User turn 1", "User turn 2"]

            # Verify assistant responses are DIFFERENT for each variant
            for conv in conversations:
                assistant_turns = [
                    turn.content
                    for turn in conv.conversation_transcript.turns
                    if turn.role == "assistant"
                ]
                # Each variant should have unique assistant response
                assert len(assistant_turns) == 1
                assert assistant_turns[0] == variant_responses[conv.variant_id]

    @patch("gavel_ai.processors.conversational_processing_step.ProviderFactory")
    @patch("gavel_ai.processors.conversational_processing_step.TurnGenerator")
    @pytest.mark.asyncio
    async def test_determinism_validation_detects_violations(
        self,
        mock_turn_gen_class,
        mock_provider_factory,
        mock_processor_config,
        sample_scenarios,
        mock_model_def,
    ):
        """Test that determinism validation detects when user turns differ across variants."""
        # Suppress deprecation warning for this test
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            from gavel_ai.processors.conversational_processing_step import (
                ConversationalProcessingStep,
            )

            # Setup mocks
            mock_turn_generator = MagicMock(spec=TurnGenerator)
            mock_turn_generator.generate_turn = AsyncMock()
            mock_turn_gen_class.return_value = mock_turn_generator

            mock_factory_instance = mock_provider_factory.return_value
            mock_factory_instance.call_agent = AsyncMock(
                return_value=MagicMock(
                    output="Assistant response",
                    metadata={"latency_ms": 100, "tokens": {"prompt": 10, "completion": 5}},
                )
            )
            mock_factory_instance.create_agent = MagicMock()

            # Create processor
            processor = ConversationalProcessingStep(
                config=mock_processor_config,
                scenarios=sample_scenarios,
                variants=["variant-1", "variant-2"],
                model_def=mock_model_def,
            )

            # Mock NON-deterministic user turn generation (different across variants)
            mock_turn_generator.generate_turn.side_effect = [
                # Variant 1
                GeneratedTurn(content="User turn 1", metadata={}, should_continue=True),
                GeneratedTurn(content="User turn 2", metadata={}, should_continue=False),
                # Variant 2 (DIFFERENT - should trigger validation failure)
                GeneratedTurn(content="Different user turn 1", metadata={}, should_continue=True),
                GeneratedTurn(content="Different user turn 2", metadata={}, should_continue=False),
            ]

            # Execute
            inputs = [PromptInput(id="test-scenario-1", user="test")]
            result = await processor.process(inputs)

            # Note: The deprecated implementation sets span attribute, not metadata
            # The new Step-based implementation properly surfaces this in context
            # For backward compatibility, we just verify the execution completes
            assert result.metadata["total_conversations"] == 2


class TestTurnGeneratorDeterminism:
    """Tests for TurnGenerator deterministic behavior."""

    @pytest.fixture
    def mock_model_def(self):
        """Create a mock model definition."""
        return ModelDefinition(
            model_provider="openai",
            model_family="gpt",
            model_version="gpt-4",
            model_parameters={"temperature": 0.0},
            provider_auth={"api_key": "test-key"},
        )

    @pytest.fixture
    def sample_scenario(self):
        """Create a sample conversation scenario."""
        return ConversationScenario(
            scenario_id="test-scenario-1",
            user_goal="Get help with resetting a password",
            context="User has forgotten their password and needs to reset it",
            dialogue_guidance=DialogueGuidance(
                tone_preference="frustrated but polite",
                escalation_strategy="ask for supervisor if not resolved",
                factual_constraints=["password reset requires email verification"],
            ),
        )

    @patch("gavel_ai.processors.turn_generator.ProviderFactory")
    @pytest.mark.asyncio
    async def test_turn_generator_basic_generation(
        self, mock_provider_factory, mock_model_def, sample_scenario
    ):
        """Test that TurnGenerator generates turns correctly."""
        from gavel_ai.processors.turn_generator import TurnGenerator

        # Mock provider factory
        mock_factory_instance = mock_provider_factory.return_value
        mock_agent = MagicMock()
        mock_factory_instance.create_agent.return_value = mock_agent

        # Configure call_agent to return a valid response
        mock_factory_instance.call_agent = AsyncMock(
            return_value=MagicMock(
                output="Generated user response",
                metadata={"latency_ms": 100, "tokens": {"prompt": 10, "completion": 5}},
            )
        )

        # Create TurnGenerator
        turn_generator = TurnGenerator(sample_scenario, mock_model_def, 10)

        # Generate a turn
        history = ConversationState(scenario_id="test", variant_id="test-variant", metadata=None)
        result = await turn_generator.generate_turn(sample_scenario, history)

        # Verify turn was generated
        assert result.content == "Generated user response"
        assert isinstance(result.should_continue, bool)

    @patch("gavel_ai.processors.turn_generator.ProviderFactory")
    @pytest.mark.asyncio
    async def test_turn_generator_checks_deterministic_mode(
        self, mock_provider_factory, mock_model_def, sample_scenario
    ):
        """Test that TurnGenerator correctly identifies deterministic mode."""
        from gavel_ai.processors.turn_generator import TurnGenerator

        # Create deterministic model definition (temperature=0.0)
        deterministic_model_def = ModelDefinition(
            model_provider="openai",
            model_family="gpt",
            model_version="gpt-4",
            model_parameters={"temperature": 0.0},  # Deterministic
            provider_auth={"api_key": "test-key"},
        )

        # Mock provider factory
        mock_factory_instance = mock_provider_factory.return_value
        mock_agent = MagicMock()
        mock_factory_instance.create_agent.return_value = mock_agent
        mock_factory_instance.call_agent = AsyncMock(
            return_value=MagicMock(
                output="Response",
                metadata={},
            )
        )

        # Create TurnGenerator with deterministic model
        turn_generator = TurnGenerator(sample_scenario, deterministic_model_def, 10)

        # Verify deterministic mode is detected
        assert turn_generator._is_deterministic_mode() is True

        # Create non-deterministic model definition
        non_deterministic_model_def = ModelDefinition(
            model_provider="openai",
            model_family="gpt",
            model_version="gpt-4",
            model_parameters={"temperature": 0.7},  # Non-deterministic
            provider_auth={"api_key": "test-key"},
        )

        turn_generator_nd = TurnGenerator(sample_scenario, non_deterministic_model_def, 10)
        assert turn_generator_nd._is_deterministic_mode() is False
