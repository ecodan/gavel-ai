"""
Unit tests for ConversationalProcessingStep.

Tests the Step-based multi-turn conversation orchestrator.
"""

import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ConfigError
from gavel_ai.core.steps import ConversationalProcessingStep
from gavel_ai.core.steps.base import StepPhase
from gavel_ai.models.config import ConversationalConfig, TurnGeneratorConfig
from gavel_ai.models.conversation import (
    ConversationResult,
    ConversationState,
)
from gavel_ai.processors.turn_generator import GeneratedTurn


def _create_mock_data_source(return_value):
    """Create a mock data source that returns the given value from read()."""
    mock_ds = MagicMock()
    mock_ds.read.return_value = return_value
    return mock_ds


class TestConversationalProcessingStep:
    """Tests for ConversationalProcessingStep."""

    @pytest.fixture
    def mock_turn_generator_config(self):
        """Create a mock TurnGeneratorConfig."""
        return TurnGeneratorConfig(
            model_id="turn-gen-model",
            temperature=0.0,
            max_tokens=500,
        )

    @pytest.fixture
    def mock_conversational_config(self, mock_turn_generator_config):
        """Create a mock ConversationalConfig."""
        return ConversationalConfig(
            max_turns=10,
            max_turn_length=2000,
            turn_generator=mock_turn_generator_config,
            timeout_seconds=300,
        )

    @pytest.fixture
    def mock_model_def_data(self):
        """Create mock model definition data."""
        return {
            "model_provider": "openai",
            "model_family": "gpt",
            "model_version": "gpt-4",
            "model_parameters": {"temperature": 0.0},
            "provider_auth": {"api_key": "test-key"},
        }

    @pytest.fixture
    def mock_agents_config(self, mock_model_def_data):
        """Create mock agents configuration."""
        return {
            "_models": {
                "turn-gen-model": mock_model_def_data,
                "variant-1": mock_model_def_data,
                "variant-2": mock_model_def_data,
            },
        }

    @pytest.fixture
    def mock_scenario_data(self):
        """Create mock scenario data (as would come from scenarios.json)."""
        return [
            {
                "scenario_id": "test-scenario-1",
                "user_goal": "Get help with resetting a password",
                "context": "User has forgotten their password",
                "dialogue_guidance": {
                    "tone_preference": "frustrated but polite",
                },
            },
        ]

    @pytest.fixture
    def mock_eval_config(self, mock_conversational_config):
        """Create a mock EvalConfig for conversational workflow."""
        mock_config = MagicMock()
        mock_config.workflow_type = "conversational"
        mock_config.conversational = mock_conversational_config
        mock_config.variants = ["variant-1", "variant-2"]
        mock_config.test_subjects = [MagicMock(prompt_name="test-subject")]
        return mock_config

    @pytest.fixture
    def mock_context(self, mock_eval_config, mock_agents_config, mock_scenario_data):
        """Create a mock RunContext."""
        mock_eval_context = MagicMock()
        mock_eval_context.eval_name = "test_eval"
        mock_eval_context.eval_config = _create_mock_data_source(mock_eval_config)
        mock_eval_context.agents = _create_mock_data_source(mock_agents_config)
        mock_eval_context.scenarios = _create_mock_data_source(mock_scenario_data)

        mock_ctx = MagicMock(spec=RunContext)
        mock_ctx.eval_context = mock_eval_context
        mock_ctx.conversation_results = None
        mock_ctx.determinism_violations = None
        mock_ctx.test_subject = None
        mock_ctx.model_variant = None
        return mock_ctx

    def test_phase_is_scenario_processing(self) -> None:
        """Test that ConversationalProcessingStep has SCENARIO_PROCESSING phase."""
        logger = logging.getLogger("test")
        step = ConversationalProcessingStep(logger)
        assert step.phase == StepPhase.SCENARIO_PROCESSING

    @pytest.mark.asyncio
    async def test_execute_requires_conversational_workflow_type(self) -> None:
        """Test that execute fails when workflow_type is not conversational."""
        logger = logging.getLogger("test")
        step = ConversationalProcessingStep(logger)

        mock_eval_config = MagicMock()
        mock_eval_config.workflow_type = "oneshot"  # Wrong type
        mock_eval_config.conversational = None

        mock_eval_context = MagicMock()
        mock_eval_context.eval_config = _create_mock_data_source(mock_eval_config)

        mock_context = MagicMock(spec=RunContext)
        mock_context.eval_context = mock_eval_context

        with pytest.raises(ConfigError, match="workflow_type='conversational'"):
            await step.execute(mock_context)

    @pytest.mark.asyncio
    async def test_execute_requires_conversational_config(self) -> None:
        """Test that execute fails when conversational config is missing."""
        logger = logging.getLogger("test")
        step = ConversationalProcessingStep(logger)

        mock_eval_config = MagicMock()
        mock_eval_config.workflow_type = "conversational"
        mock_eval_config.conversational = None

        mock_eval_context = MagicMock()
        mock_eval_context.eval_config = _create_mock_data_source(mock_eval_config)

        mock_context = MagicMock(spec=RunContext)
        mock_context.eval_context = mock_eval_context

        with pytest.raises(ConfigError, match="Conversational config not found"):
            await step.execute(mock_context)

    @pytest.mark.asyncio
    async def test_execute_requires_variants(
        self, mock_context, mock_conversational_config
    ) -> None:
        """Test that execute fails when no variants configured."""
        logger = logging.getLogger("test")
        step = ConversationalProcessingStep(logger)

        # Override variants to empty
        mock_eval_config = MagicMock()
        mock_eval_config.workflow_type = "conversational"
        mock_eval_config.conversational = mock_conversational_config
        mock_eval_config.variants = []

        mock_context.eval_context.eval_config = _create_mock_data_source(mock_eval_config)

        with pytest.raises(ConfigError, match="No variants configured"):
            await step.execute(mock_context)

    @pytest.mark.asyncio
    @patch("gavel_ai.core.steps.conversational_processor.TurnGenerator")
    @patch("gavel_ai.core.steps.conversational_processor.ProviderFactory")
    async def test_execute_processes_conversations(
        self,
        mock_provider_factory_class,
        mock_turn_generator_class,
        mock_context,
    ) -> None:
        """Test that execute processes conversations across scenarios × variants."""
        logger = logging.getLogger("test")
        step = ConversationalProcessingStep(logger)

        # Setup TurnGenerator mock
        mock_turn_generator = MagicMock()
        mock_turn_generator.generate_turn = AsyncMock()
        mock_turn_generator_class.return_value = mock_turn_generator

        # Configure turn generation - 2 turns then stop
        mock_turn_generator.generate_turn.side_effect = [
            # Variant 1: 2 user turns
            GeneratedTurn(content="User turn 1", metadata={}, should_continue=True),
            GeneratedTurn(content="User turn 2", metadata={}, should_continue=False),
            # Variant 2: Same 2 user turns (deterministic)
            GeneratedTurn(content="User turn 1", metadata={}, should_continue=True),
            GeneratedTurn(content="User turn 2", metadata={}, should_continue=False),
        ]

        # Setup ProviderFactory mock
        mock_factory = MagicMock()
        mock_provider_factory_class.return_value = mock_factory
        mock_factory.create_agent = MagicMock(return_value=MagicMock())
        mock_factory.call_agent = AsyncMock(
            return_value=MagicMock(
                output="Assistant response",
                metadata={"latency_ms": 100, "tokens": {"prompt": 10, "completion": 5}},
            )
        )

        # Override the step's provider_factory
        step.provider_factory = mock_factory

        await step.execute(mock_context)

        # Verify conversation results were set
        assert mock_context.conversation_results is not None
        assert len(mock_context.conversation_results) == 2  # 1 scenario × 2 variants
        assert mock_context.determinism_violations == []

        # Verify test_subject and model_variant set
        assert mock_context.test_subject == "test-subject"
        assert mock_context.model_variant == "variant-1"

        # ✅ AC#2 VERIFICATION: All variants receive identical user turns
        variant_1_result = mock_context.conversation_results[0]
        variant_2_result = mock_context.conversation_results[1]

        # Extract user turns from each variant
        variant_1_user_turns = [
            turn.content
            for turn in variant_1_result.conversation_transcript.turns
            if turn.role == "user"
        ]
        variant_2_user_turns = [
            turn.content
            for turn in variant_2_result.conversation_transcript.turns
            if turn.role == "user"
        ]

        # Critical assertion: User turns must be identical across variants
        assert variant_1_user_turns == variant_2_user_turns, (
            f"User turns not identical across variants! "
            f"Variant 1: {variant_1_user_turns}, Variant 2: {variant_2_user_turns}"
        )
        # Only first user turn is added - second generated turn has should_continue=False
        # so it is not added to the transcript (per implementation lines 350-361)
        assert variant_1_user_turns == ["User turn 1"]

        # Verify assistant responses are different (unique to each variant)
        variant_1_assistant_turns = [
            turn.content
            for turn in variant_1_result.conversation_transcript.turns
            if turn.role == "assistant"
        ]
        variant_2_assistant_turns = [
            turn.content
            for turn in variant_2_result.conversation_transcript.turns
            if turn.role == "assistant"
        ]
        # Both should have same assistant response (mock returns same response)
        assert variant_1_assistant_turns == variant_2_assistant_turns

    @pytest.mark.asyncio
    @patch("gavel_ai.core.steps.conversational_processor.TurnGenerator")
    @patch("gavel_ai.core.steps.conversational_processor.ProviderFactory")
    async def test_determinism_validation_detects_violations(
        self,
        mock_provider_factory_class,
        mock_turn_generator_class,
        mock_context,
    ) -> None:
        """Test that determinism validation detects when user turns differ across variants."""
        logger = logging.getLogger("test")
        step = ConversationalProcessingStep(logger)

        # Setup TurnGenerator mock
        mock_turn_generator = MagicMock()
        mock_turn_generator.generate_turn = AsyncMock()
        mock_turn_generator_class.return_value = mock_turn_generator

        # Configure NON-deterministic turn generation
        mock_turn_generator.generate_turn.side_effect = [
            # Variant 1
            GeneratedTurn(content="User turn 1", metadata={}, should_continue=True),
            GeneratedTurn(content="User turn 2", metadata={}, should_continue=False),
            # Variant 2: DIFFERENT turns (violation!)
            GeneratedTurn(content="Different turn 1", metadata={}, should_continue=True),
            GeneratedTurn(content="Different turn 2", metadata={}, should_continue=False),
        ]

        # Setup ProviderFactory mock
        mock_factory = MagicMock()
        mock_provider_factory_class.return_value = mock_factory
        mock_factory.create_agent = MagicMock(return_value=MagicMock())
        mock_factory.call_agent = AsyncMock(
            return_value=MagicMock(
                output="Assistant response",
                metadata={"latency_ms": 100, "tokens": {"prompt": 10, "completion": 5}},
            )
        )

        step.provider_factory = mock_factory

        await step.execute(mock_context)

        # Verify determinism violation was detected
        assert mock_context.determinism_violations is not None
        assert len(mock_context.determinism_violations) == 1
        assert mock_context.determinism_violations[0]["scenario_id"] == "test-scenario-1"

    @pytest.mark.asyncio
    @patch("gavel_ai.core.steps.conversational_processor.TurnGenerator")
    @patch("gavel_ai.core.steps.conversational_processor.ProviderFactory")
    async def test_execute_handles_conversation_errors(
        self,
        mock_provider_factory_class,
        mock_turn_generator_class,
        mock_context,
    ) -> None:
        """Test that execute handles conversation execution errors gracefully."""
        logger = logging.getLogger("test")
        step = ConversationalProcessingStep(logger)

        # Setup TurnGenerator mock
        mock_turn_generator = MagicMock()
        mock_turn_generator.generate_turn = AsyncMock()
        mock_turn_generator_class.return_value = mock_turn_generator

        # Both variants need turns that trigger LLM calls
        mock_turn_generator.generate_turn.side_effect = [
            # Variant 1: needs LLM call (should_continue=True), then ends
            GeneratedTurn(content="User turn 1", metadata={}, should_continue=True),
            GeneratedTurn(content="User turn 2", metadata={}, should_continue=False),
            # Variant 2: needs LLM call but will fail
            GeneratedTurn(content="User turn 1", metadata={}, should_continue=True),
        ]

        # Setup ProviderFactory mock - first call succeeds, second fails
        mock_factory = MagicMock()
        mock_provider_factory_class.return_value = mock_factory
        mock_factory.create_agent = MagicMock(return_value=MagicMock())

        call_count = 0

        async def mock_call_agent(agent, prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First variant's LLM call succeeds
                return MagicMock(
                    output="Assistant response",
                    metadata={"latency_ms": 100, "tokens": {"prompt": 10, "completion": 5}},
                )
            else:
                # Second variant's LLM call fails
                raise Exception("API Error")

        mock_factory.call_agent = mock_call_agent

        step.provider_factory = mock_factory

        await step.execute(mock_context)

        # Verify we got results for both variants (one successful, one error)
        assert mock_context.conversation_results is not None
        assert len(mock_context.conversation_results) == 2

        # First result should succeed (completed conversation)
        assert mock_context.conversation_results[0].error is None
        assert mock_context.conversation_results[0].completed is True

        # Second result should have error
        assert mock_context.conversation_results[1].error is not None
        assert "API Error" in mock_context.conversation_results[1].error


class TestConversationalProcessingStepDeterminism:
    """Tests for determinism validation in ConversationalProcessingStep."""

    def test_validate_determinism_returns_none_for_single_variant(self) -> None:
        """Test that validation returns None when only one variant."""
        logger = logging.getLogger("test")
        step = ConversationalProcessingStep(logger)

        results = [
            ConversationResult(
                scenario_id="s1",
                variant_id="v1",
                conversation_transcript=ConversationState(
                    scenario_id="s1", variant_id="v1", metadata=None
                ),
                results_raw=[],
                duration_ms=100,
                completed=True,
                tokens_total=0,
                error=None,
                timestamp=datetime.now(UTC),
            )
        ]

        violation = step._validate_determinism("s1", results)
        assert violation is None

    def test_validate_determinism_passes_for_identical_turns(self) -> None:
        """Test that validation passes when user turns are identical."""
        logger = logging.getLogger("test")
        step = ConversationalProcessingStep(logger)

        # Create two results with identical user turns
        conv1 = ConversationState(scenario_id="s1", variant_id="v1", metadata=None)
        conv1.add_turn("user", "Hello")
        conv1.add_turn("assistant", "Hi there!")
        conv1.add_turn("user", "How are you?")

        conv2 = ConversationState(scenario_id="s1", variant_id="v2", metadata=None)
        conv2.add_turn("user", "Hello")  # Same
        conv2.add_turn("assistant", "Greetings!")  # Different assistant
        conv2.add_turn("user", "How are you?")  # Same

        results = [
            ConversationResult(
                scenario_id="s1",
                variant_id="v1",
                conversation_transcript=conv1,
                results_raw=[],
                duration_ms=100,
                completed=True,
                tokens_total=0,
                error=None,
                timestamp=datetime.now(UTC),
            ),
            ConversationResult(
                scenario_id="s1",
                variant_id="v2",
                conversation_transcript=conv2,
                results_raw=[],
                duration_ms=100,
                completed=True,
                tokens_total=0,
                error=None,
                timestamp=datetime.now(UTC),
            ),
        ]

        violation = step._validate_determinism("s1", results)
        assert violation is None

    def test_validate_determinism_fails_for_different_turns(self) -> None:
        """Test that validation fails when user turns differ."""
        logger = logging.getLogger("test")
        step = ConversationalProcessingStep(logger)

        conv1 = ConversationState(scenario_id="s1", variant_id="v1", metadata=None)
        conv1.add_turn("user", "Hello")

        conv2 = ConversationState(scenario_id="s1", variant_id="v2", metadata=None)
        conv2.add_turn("user", "Hi there")  # Different!

        results = [
            ConversationResult(
                scenario_id="s1",
                variant_id="v1",
                conversation_transcript=conv1,
                results_raw=[],
                duration_ms=100,
                completed=True,
                tokens_total=0,
                error=None,
                timestamp=datetime.now(UTC),
            ),
            ConversationResult(
                scenario_id="s1",
                variant_id="v2",
                conversation_transcript=conv2,
                results_raw=[],
                duration_ms=100,
                completed=True,
                tokens_total=0,
                error=None,
                timestamp=datetime.now(UTC),
            ),
        ]

        violation = step._validate_determinism("s1", results)
        assert violation is not None
        assert violation["scenario_id"] == "s1"
        assert violation["baseline_variant"] == "v1"
        assert violation["variant_id"] == "v2"
        assert violation["baseline_user_turns"] == ["Hello"]
        assert violation["variant_user_turns"] == ["Hi there"]


class TestConversationalProcessingStepScenarioLoading:
    """Tests for scenario loading validation in ConversationalProcessingStep."""

    def test_load_conversation_scenarios_with_valid_and_invalid_scenarios(self) -> None:
        """Test that scenario loading skips invalid scenarios with missing required fields."""
        logger = logging.getLogger("test")
        step = ConversationalProcessingStep(logger)

        # Create mock context with mixed valid/invalid scenarios
        mock_scenario_data = [
            # Valid scenario 1
            {
                "scenario_id": "valid-1",
                "user_goal": "Get password help",
                "context": "User forgot password",
                "dialogue_guidance": {"tone": "polite"},
            },
            # Invalid: missing user_goal
            {
                "scenario_id": "invalid-1",
                "context": "No user goal provided",
            },
            # Valid scenario 2
            {
                "id": "valid-2",  # Uses 'id' instead of 'scenario_id'
                "input": "Request account deletion",  # Uses 'input' instead of 'user_goal'
                "context": "User wants to delete account",
            },
            # Invalid: missing both scenario_id and id
            {
                "user_goal": "Some goal",
                "context": "No scenario ID",
            },
        ]

        mock_eval_context = MagicMock()
        mock_eval_context.scenarios = _create_mock_data_source(mock_scenario_data)

        mock_context = MagicMock(spec=RunContext)
        mock_context.eval_context = mock_eval_context

        # Load scenarios
        scenarios = step._load_conversation_scenarios(mock_context)

        # Should load 2 valid scenarios, skip 2 invalid
        assert len(scenarios) == 2
        assert scenarios[0].scenario_id == "valid-1"
        assert scenarios[0].user_goal == "Get password help"
        assert scenarios[1].scenario_id == "valid-2"
        assert scenarios[1].user_goal == "Request account deletion"

    def test_load_conversation_scenarios_handles_model_objects(self) -> None:
        """Test that scenario loading handles Pydantic model objects with model_dump()."""
        logger = logging.getLogger("test")
        step = ConversationalProcessingStep(logger)

        # Create mock Pydantic model object
        mock_model = MagicMock()
        mock_model.model_dump.return_value = {
            "scenario_id": "model-scenario",
            "user_goal": "Test goal",
            "context": "Test context",
        }

        mock_eval_context = MagicMock()
        mock_eval_context.scenarios = _create_mock_data_source([mock_model])

        mock_context = MagicMock(spec=RunContext)
        mock_context.eval_context = mock_eval_context

        scenarios = step._load_conversation_scenarios(mock_context)

        assert len(scenarios) == 1
        assert scenarios[0].scenario_id == "model-scenario"
        assert scenarios[0].user_goal == "Test goal"
