"""
Unit tests for TurnGenerator component.

Tests:
- Determinism: same inputs → same output with temperature=0
- Goal detection: various goal states
- Max turns boundary: should_continue=False after max_turns
- Edge cases: empty history, very long history, circular conversation
- Mock LLM provider for reliable tests
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gavel_ai.models.agents import ModelDefinition
from gavel_ai.models.conversation import (
    ConversationScenario,
    ConversationState,
    DialogueGuidance,
)
from gavel_ai.processors.turn_generator import GeneratedTurn, TurnGenerator
from gavel_ai.providers.factory import ProviderResult


class TestGeneratedTurn:
    """Tests for GeneratedTurn Pydantic model."""

    def test_generated_turn_creation(self):
        """GeneratedTurn can be created with required fields."""
        turn = GeneratedTurn(
            content="Hello, I need help",
            metadata={"tokens": 10},
            should_continue=True,
        )
        assert turn.content == "Hello, I need help"
        assert turn.metadata == {"tokens": 10}
        assert turn.should_continue is True

    def test_generated_turn_requires_content(self):
        """GeneratedTurn requires content field."""
        with pytest.raises(ValueError):
            GeneratedTurn(
                metadata={},
                should_continue=True,
            )

    def test_generated_turn_requires_should_continue(self):
        """GeneratedTurn requires should_continue field."""
        with pytest.raises(ValueError):
            GeneratedTurn(
                content="Hello",
                metadata={},
            )


class TestTurnGeneratorInit:
    """Tests for TurnGenerator initialization."""

    @pytest.fixture
    def valid_scenario(self) -> ConversationScenario:
        """Create a valid ConversationScenario for testing."""
        return ConversationScenario(
            scenario_id="test-scenario-1",
            user_goal="Book a flight from NYC to LAX",
            context="User is a business traveler",
        )

    @pytest.fixture
    def valid_model_def(self) -> ModelDefinition:
        """Create a valid ModelDefinition for testing."""
        return ModelDefinition(
            model_provider="anthropic",
            model_family="claude",
            model_version="claude-3-sonnet-20240229",
            model_parameters={"temperature": 0.0},
            provider_auth={"api_key": "test-key"},
        )

    def test_init_with_valid_inputs(
        self, valid_scenario: ConversationScenario, valid_model_def: ModelDefinition
    ):
        """TurnGenerator initializes with valid scenario and model_def."""
        with patch.object(TurnGenerator, "_validate_inputs"):
            with patch("gavel_ai.processors.turn_generator.ProviderFactory") as mock_factory:
                mock_factory.return_value.create_agent.return_value = MagicMock()
                generator = TurnGenerator(
                    scenario=valid_scenario,
                    model_def=valid_model_def,
                    max_turns=10,
                )
                assert generator.scenario == valid_scenario
                assert generator.model_def == valid_model_def
                assert generator._max_turns == 10

    def test_init_rejects_empty_user_goal(self, valid_model_def: ModelDefinition):
        """TurnGenerator rejects scenario with empty user_goal."""
        with pytest.raises(ValueError, match="user_goal cannot be empty"):
            ConversationScenario(
                scenario_id="test-1",
                user_goal="",  # Empty user_goal
            )

    def test_init_rejects_whitespace_user_goal(self, valid_model_def: ModelDefinition):
        """TurnGenerator rejects scenario with whitespace-only user_goal."""
        with pytest.raises(ValueError, match="user_goal cannot be empty"):
            ConversationScenario(
                scenario_id="test-1",
                user_goal="   ",  # Whitespace-only user_goal
            )

    def test_init_rejects_missing_provider(self, valid_scenario: ConversationScenario):
        """TurnGenerator rejects model_def without provider."""
        model_def = ModelDefinition(
            model_provider="",  # Empty provider
            model_family="claude",
            model_version="claude-3-sonnet",
            model_parameters={},
            provider_auth={"api_key": "test-key"},
        )
        # TurnGenerator's _validate_inputs should reject empty provider
        with pytest.raises(ValueError, match="provider"):
            with patch("gavel_ai.processors.turn_generator.ProviderFactory") as mock_factory:
                mock_factory.return_value.create_agent.return_value = MagicMock()
                TurnGenerator(scenario=valid_scenario, model_def=model_def)


class TestTurnGeneratorDeterminism:
    """Tests for deterministic turn generation (AC #2)."""

    @pytest.fixture
    def scenario(self) -> ConversationScenario:
        """Create a test scenario."""
        return ConversationScenario(
            scenario_id="determinism-test",
            user_goal="Reset my password",
            context="User forgot password last week",
        )

    @pytest.fixture
    def deterministic_model_def(self) -> ModelDefinition:
        """Create model definition with temperature=0 for determinism."""
        return ModelDefinition(
            model_provider="anthropic",
            model_family="claude",
            model_version="claude-3-sonnet-20240229",
            model_parameters={"temperature": 0.0},  # Deterministic
            provider_auth={"api_key": "test-key"},
        )

    @pytest.fixture
    def non_deterministic_model_def(self) -> ModelDefinition:
        """Create model definition with temperature>0."""
        return ModelDefinition(
            model_provider="anthropic",
            model_family="claude",
            model_version="claude-3-sonnet-20240229",
            model_parameters={"temperature": 0.7},  # Non-deterministic
            provider_auth={"api_key": "test-key"},
        )

    def test_is_deterministic_mode_true(
        self, scenario: ConversationScenario, deterministic_model_def: ModelDefinition
    ):
        """TurnGenerator detects deterministic mode (temperature=0)."""
        with patch("gavel_ai.processors.turn_generator.ProviderFactory") as mock_factory:
            mock_factory.return_value.create_agent.return_value = MagicMock()
            generator = TurnGenerator(scenario=scenario, model_def=deterministic_model_def)
            assert generator._is_deterministic_mode() is True

    def test_is_deterministic_mode_false(
        self, scenario: ConversationScenario, non_deterministic_model_def: ModelDefinition
    ):
        """TurnGenerator detects non-deterministic mode (temperature>0)."""
        with patch("gavel_ai.processors.turn_generator.ProviderFactory") as mock_factory:
            mock_factory.return_value.create_agent.return_value = MagicMock()
            generator = TurnGenerator(scenario=scenario, model_def=non_deterministic_model_def)
            assert generator._is_deterministic_mode() is False

    @pytest.mark.asyncio
    async def test_same_inputs_produce_same_output(
        self, scenario: ConversationScenario, deterministic_model_def: ModelDefinition
    ):
        """Same scenario and history produce identical turns with temperature=0."""
        with patch("gavel_ai.processors.turn_generator.ProviderFactory") as mock_factory:
            mock_agent = MagicMock()
            mock_factory_instance = mock_factory.return_value
            mock_factory_instance.create_agent.return_value = mock_agent

            # Mock LLM to return same response every time
            mock_factory_instance.call_agent = AsyncMock(
                return_value=ProviderResult(
                    output="I need to reset my password please",
                    metadata={"tokens": {"prompt": 50, "completion": 10}},
                )
            )

            generator = TurnGenerator(scenario=scenario, model_def=deterministic_model_def)

            # Create identical conversation states
            state1 = ConversationState(scenario_id="determinism-test", variant_id="v1")
            state2 = ConversationState(scenario_id="determinism-test", variant_id="v1")

            # Generate turns for identical inputs
            turn1 = await generator.generate_turn(scenario, state1)
            turn2 = await generator.generate_turn(scenario, state2)

            # With mocked deterministic LLM, outputs should be identical
            assert turn1.content == turn2.content
            assert turn1.should_continue == turn2.should_continue


class TestTurnGeneratorGoalDetection:
    """Tests for goal detection (AC #4)."""

    @pytest.fixture
    def scenario(self) -> ConversationScenario:
        """Create a test scenario."""
        return ConversationScenario(
            scenario_id="goal-test",
            user_goal="Get help with account",
        )

    @pytest.fixture
    def model_def(self) -> ModelDefinition:
        """Create model definition."""
        return ModelDefinition(
            model_provider="anthropic",
            model_family="claude",
            model_version="claude-3-sonnet-20240229",
            model_parameters={"temperature": 0.0},
            provider_auth={"api_key": "test-key"},
        )

    @pytest.fixture
    def generator(
        self, scenario: ConversationScenario, model_def: ModelDefinition
    ) -> TurnGenerator:
        """Create a TurnGenerator instance with mocked provider."""
        with patch("gavel_ai.processors.turn_generator.ProviderFactory") as mock_factory:
            mock_factory.return_value.create_agent.return_value = MagicMock()
            gen = TurnGenerator(scenario=scenario, model_def=model_def, max_turns=5)
            return gen

    def test_goal_achieved_with_thank_you(
        self, generator: TurnGenerator, scenario: ConversationScenario
    ):
        """Goal is detected when user says 'thank you'."""
        state = ConversationState(scenario_id="goal-test", variant_id="v1")
        result = generator._should_continue(scenario, state, "Thank you so much for your help!")
        assert result is False  # Should not continue - goal achieved

    def test_goal_achieved_with_thanks(
        self, generator: TurnGenerator, scenario: ConversationScenario
    ):
        """Goal is detected when user says 'thanks'."""
        state = ConversationState(scenario_id="goal-test", variant_id="v1")
        result = generator._should_continue(scenario, state, "Thanks, that worked perfectly!")
        assert result is False

    def test_goal_achieved_with_perfect(
        self, generator: TurnGenerator, scenario: ConversationScenario
    ):
        """Goal is detected when user says 'perfect'."""
        state = ConversationState(scenario_id="goal-test", variant_id="v1")
        result = generator._should_continue(scenario, state, "Perfect, my issue is resolved.")
        assert result is False

    def test_goal_achieved_with_worked(
        self, generator: TurnGenerator, scenario: ConversationScenario
    ):
        """Goal is detected when user says 'worked'."""
        state = ConversationState(scenario_id="goal-test", variant_id="v1")
        result = generator._should_continue(
            scenario, state, "That worked! I can access my account now."
        )
        assert result is False

    def test_goal_achieved_with_resolved(
        self, generator: TurnGenerator, scenario: ConversationScenario
    ):
        """Goal is detected when user says 'resolved'."""
        state = ConversationState(scenario_id="goal-test", variant_id="v1")
        result = generator._should_continue(scenario, state, "My issue has been resolved.")
        assert result is False

    def test_negation_avoids_false_positive(
        self, generator: TurnGenerator, scenario: ConversationScenario
    ):
        """Negated goal words don't trigger false positive."""
        state = ConversationState(scenario_id="goal-test", variant_id="v1")
        # "not worked" should NOT be detected as goal achieved
        result = generator._should_continue(scenario, state, "That has not worked for me.")
        assert result is True  # Should continue - goal NOT achieved

    def test_continues_when_no_goal_indicators(
        self, generator: TurnGenerator, scenario: ConversationScenario
    ):
        """Conversation continues when no goal indicators present."""
        state = ConversationState(scenario_id="goal-test", variant_id="v1")
        result = generator._should_continue(scenario, state, "I still need help with this problem.")
        assert result is True  # Should continue


class TestTurnGeneratorMaxTurns:
    """Tests for max turns boundary (AC #4)."""

    @pytest.fixture
    def scenario(self) -> ConversationScenario:
        """Create a test scenario."""
        return ConversationScenario(
            scenario_id="max-turns-test",
            user_goal="Complete a multi-step task",
        )

    @pytest.fixture
    def model_def(self) -> ModelDefinition:
        """Create model definition."""
        return ModelDefinition(
            model_provider="anthropic",
            model_family="claude",
            model_version="claude-3-sonnet-20240229",
            model_parameters={"temperature": 0.0},
            provider_auth={"api_key": "test-key"},
        )

    def test_should_continue_false_at_max_turns(
        self, scenario: ConversationScenario, model_def: ModelDefinition
    ):
        """should_continue=False when max_turns reached."""
        with patch("gavel_ai.processors.turn_generator.ProviderFactory") as mock_factory:
            mock_factory.return_value.create_agent.return_value = MagicMock()
            generator = TurnGenerator(scenario=scenario, model_def=model_def, max_turns=3)

            # Create state with 3 turns (at max)
            state = ConversationState(scenario_id="max-turns-test", variant_id="v1")
            state.add_turn("user", "Turn 1")
            state.add_turn("assistant", "Response 1")
            state.add_turn("user", "Turn 2")

            # At max_turns, should not continue
            result = generator._should_continue(scenario, state, "More questions please")
            assert result is False

    def test_should_continue_true_before_max_turns(
        self, scenario: ConversationScenario, model_def: ModelDefinition
    ):
        """should_continue=True before max_turns reached."""
        with patch("gavel_ai.processors.turn_generator.ProviderFactory") as mock_factory:
            mock_factory.return_value.create_agent.return_value = MagicMock()
            generator = TurnGenerator(scenario=scenario, model_def=model_def, max_turns=5)

            # Create state with 2 turns (below max)
            state = ConversationState(scenario_id="max-turns-test", variant_id="v1")
            state.add_turn("user", "Turn 1")
            state.add_turn("assistant", "Response 1")

            # Below max_turns, should continue
            result = generator._should_continue(scenario, state, "I have another question")
            assert result is True

    def test_default_max_turns(self, scenario: ConversationScenario, model_def: ModelDefinition):
        """Default max_turns is 10."""
        with patch("gavel_ai.processors.turn_generator.ProviderFactory") as mock_factory:
            mock_factory.return_value.create_agent.return_value = MagicMock()
            generator = TurnGenerator(scenario=scenario, model_def=model_def)
            assert generator._max_turns == 10


class TestTurnGeneratorEdgeCases:
    """Tests for edge cases."""

    @pytest.fixture
    def scenario(self) -> ConversationScenario:
        """Create a test scenario."""
        return ConversationScenario(
            scenario_id="edge-case-test",
            user_goal="Test edge cases",
        )

    @pytest.fixture
    def model_def(self) -> ModelDefinition:
        """Create model definition."""
        return ModelDefinition(
            model_provider="anthropic",
            model_family="claude",
            model_version="claude-3-sonnet-20240229",
            model_parameters={"temperature": 0.0},
            provider_auth={"api_key": "test-key"},
        )

    @pytest.mark.asyncio
    async def test_empty_history(self, scenario: ConversationScenario, model_def: ModelDefinition):
        """TurnGenerator handles empty conversation history."""
        with patch("gavel_ai.processors.turn_generator.ProviderFactory") as mock_factory:
            mock_agent = MagicMock()
            mock_factory_instance = mock_factory.return_value
            mock_factory_instance.create_agent.return_value = mock_agent
            mock_factory_instance.call_agent = AsyncMock(
                return_value=ProviderResult(
                    output="Hello, I need help with my account",
                    metadata={"tokens": {"prompt": 30, "completion": 8}},
                )
            )

            generator = TurnGenerator(scenario=scenario, model_def=model_def)

            # Empty history
            state = ConversationState(scenario_id="edge-case-test", variant_id="v1")
            assert len(state.turns) == 0

            turn = await generator.generate_turn(scenario, state)
            assert turn.content is not None
            assert len(turn.content) > 0

    @pytest.mark.asyncio
    async def test_long_history(self, scenario: ConversationScenario, model_def: ModelDefinition):
        """TurnGenerator handles long conversation history."""
        with patch("gavel_ai.processors.turn_generator.ProviderFactory") as mock_factory:
            mock_agent = MagicMock()
            mock_factory_instance = mock_factory.return_value
            mock_factory_instance.create_agent.return_value = mock_agent
            mock_factory_instance.call_agent = AsyncMock(
                return_value=ProviderResult(
                    output="Let me continue with this issue",
                    metadata={"tokens": {"prompt": 500, "completion": 10}},
                )
            )

            generator = TurnGenerator(scenario=scenario, model_def=model_def, max_turns=100)

            # Long history with many turns
            state = ConversationState(scenario_id="edge-case-test", variant_id="v1")
            for i in range(20):
                state.add_turn("user", f"User message {i}")
                state.add_turn("assistant", f"Assistant response {i}")

            assert len(state.turns) == 40

            turn = await generator.generate_turn(scenario, state)
            assert turn.content is not None

    def test_history_property_empty(
        self, scenario: ConversationScenario, model_def: ModelDefinition
    ):
        """History property returns empty string for empty state."""
        state = ConversationState(scenario_id="edge-case-test", variant_id="v1")
        assert state.history == ""

    def test_history_property_with_turns(
        self, scenario: ConversationScenario, model_def: ModelDefinition
    ):
        """History property returns formatted string."""
        state = ConversationState(scenario_id="edge-case-test", variant_id="v1")
        state.add_turn("user", "Hello")
        state.add_turn("assistant", "Hi there!")

        expected = "user: Hello\nassistant: Hi there!"
        assert state.history == expected


class TestTurnGeneratorPromptBuilding:
    """Tests for prompt construction."""

    @pytest.fixture
    def scenario_with_guidance(self) -> ConversationScenario:
        """Create a scenario with dialogue guidance."""
        return ConversationScenario(
            scenario_id="prompt-test",
            user_goal="Book a flight",
            context="User is a business traveler",
            dialogue_guidance=DialogueGuidance(
                tone_preference="professional",
                escalation_strategy="politely insist",
                factual_constraints=["Prefers aisle seat", "Needs WiFi"],
            ),
        )

    @pytest.fixture
    def model_def(self) -> ModelDefinition:
        """Create model definition."""
        return ModelDefinition(
            model_provider="anthropic",
            model_family="claude",
            model_version="claude-3-sonnet-20240229",
            model_parameters={"temperature": 0.0},
            provider_auth={"api_key": "test-key"},
        )

    def test_prompt_includes_scenario_goal(
        self, scenario_with_guidance: ConversationScenario, model_def: ModelDefinition
    ):
        """Built prompt includes user_goal."""
        with patch("gavel_ai.processors.turn_generator.ProviderFactory") as mock_factory:
            mock_factory.return_value.create_agent.return_value = MagicMock()
            generator = TurnGenerator(scenario=scenario_with_guidance, model_def=model_def)

            state = ConversationState(scenario_id="prompt-test", variant_id="v1")
            prompt = generator._build_turn_prompt(scenario_with_guidance, state)

            assert "Book a flight" in prompt

    def test_prompt_includes_context(
        self, scenario_with_guidance: ConversationScenario, model_def: ModelDefinition
    ):
        """Built prompt includes context."""
        with patch("gavel_ai.processors.turn_generator.ProviderFactory") as mock_factory:
            mock_factory.return_value.create_agent.return_value = MagicMock()
            generator = TurnGenerator(scenario=scenario_with_guidance, model_def=model_def)

            state = ConversationState(scenario_id="prompt-test", variant_id="v1")
            prompt = generator._build_turn_prompt(scenario_with_guidance, state)

            assert "business traveler" in prompt

    def test_prompt_includes_dialogue_guidance(
        self, scenario_with_guidance: ConversationScenario, model_def: ModelDefinition
    ):
        """Built prompt includes dialogue guidance elements."""
        with patch("gavel_ai.processors.turn_generator.ProviderFactory") as mock_factory:
            mock_factory.return_value.create_agent.return_value = MagicMock()
            generator = TurnGenerator(scenario=scenario_with_guidance, model_def=model_def)

            state = ConversationState(scenario_id="prompt-test", variant_id="v1")
            prompt = generator._build_turn_prompt(scenario_with_guidance, state)

            assert "professional" in prompt
            assert "politely insist" in prompt
            assert "aisle seat" in prompt

    def test_prompt_includes_history(
        self, scenario_with_guidance: ConversationScenario, model_def: ModelDefinition
    ):
        """Built prompt includes conversation history."""
        with patch("gavel_ai.processors.turn_generator.ProviderFactory") as mock_factory:
            mock_factory.return_value.create_agent.return_value = MagicMock()
            generator = TurnGenerator(scenario=scenario_with_guidance, model_def=model_def)

            state = ConversationState(scenario_id="prompt-test", variant_id="v1")
            state.add_turn("user", "I need to book a flight")
            state.add_turn("assistant", "Where would you like to fly?")

            prompt = generator._build_turn_prompt(scenario_with_guidance, state)

            assert "I need to book a flight" in prompt
            assert "Where would you like to fly?" in prompt


class TestTurnGeneratorTelemetry:
    """Tests for telemetry emission (AC #2, #3)."""

    @pytest.fixture
    def scenario(self) -> ConversationScenario:
        """Create a test scenario."""
        return ConversationScenario(
            scenario_id="telemetry-test",
            user_goal="Test telemetry",
        )

    @pytest.fixture
    def model_def(self) -> ModelDefinition:
        """Create model definition."""
        return ModelDefinition(
            model_provider="anthropic",
            model_family="claude",
            model_version="claude-3-sonnet-20240229",
            model_parameters={"temperature": 0.0},
            provider_auth={"api_key": "test-key"},
        )

    @pytest.mark.asyncio
    async def test_span_emitted_on_generate_turn(
        self, scenario: ConversationScenario, model_def: ModelDefinition
    ):
        """Telemetry span is emitted during generate_turn."""
        with patch("gavel_ai.processors.turn_generator.ProviderFactory") as mock_factory:
            mock_agent = MagicMock()
            mock_factory_instance = mock_factory.return_value
            mock_factory_instance.create_agent.return_value = mock_agent
            mock_factory_instance.call_agent = AsyncMock(
                return_value=ProviderResult(
                    output="Test response",
                    metadata={"tokens": {"prompt": 50, "completion": 10}},
                )
            )

            with patch("gavel_ai.processors.turn_generator.get_tracer") as mock_get_tracer:
                mock_tracer = MagicMock()
                mock_span = MagicMock()
                mock_span.__enter__ = MagicMock(return_value=mock_span)
                mock_span.__exit__ = MagicMock(return_value=None)
                mock_tracer.start_as_current_span.return_value = mock_span
                mock_get_tracer.return_value = mock_tracer

                generator = TurnGenerator(scenario=scenario, model_def=model_def)
                state = ConversationState(scenario_id="telemetry-test", variant_id="v1")

                await generator.generate_turn(scenario, state)

                # Verify span was started with correct name
                mock_tracer.start_as_current_span.assert_called_with("generate_turn")

    @pytest.mark.asyncio
    async def test_span_includes_attributes(
        self, scenario: ConversationScenario, model_def: ModelDefinition
    ):
        """Telemetry span includes required attributes."""
        with patch("gavel_ai.processors.turn_generator.ProviderFactory") as mock_factory:
            mock_agent = MagicMock()
            mock_factory_instance = mock_factory.return_value
            mock_factory_instance.create_agent.return_value = mock_agent
            mock_factory_instance.call_agent = AsyncMock(
                return_value=ProviderResult(
                    output="Test response",
                    metadata={"tokens": {"prompt": 50, "completion": 10}},
                )
            )

            with patch("gavel_ai.processors.turn_generator.get_tracer") as mock_get_tracer:
                mock_tracer = MagicMock()
                mock_span = MagicMock()
                mock_span.__enter__ = MagicMock(return_value=mock_span)
                mock_span.__exit__ = MagicMock(return_value=None)
                mock_tracer.start_as_current_span.return_value = mock_span
                mock_get_tracer.return_value = mock_tracer

                generator = TurnGenerator(scenario=scenario, model_def=model_def)
                state = ConversationState(scenario_id="telemetry-test", variant_id="v1")

                await generator.generate_turn(scenario, state)

                # Check that set_attribute was called with expected attributes
                attribute_calls = {
                    call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list
                }

                assert "scenario_id" in attribute_calls
                assert attribute_calls["scenario_id"] == "telemetry-test"
                assert "total_turns" in attribute_calls
                assert "should_continue" in attribute_calls
