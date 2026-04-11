import pytest

pytestmark = pytest.mark.unit
"""
Unit tests for conversation models and loading utilities.

Tests for:
- DialogueGuidance
- ConversationScenario
- TurnMetadata
- Turn
- ConversationState
- load_conversation_scenarios
- iter_conversation_scenarios
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from gavel_ai.models.conversation import (
    ConversationResult,
    ConversationScenario,
    ConversationState,
    DialogueGuidance,
    Turn,
    TurnMetadata,
    TurnResult,
    iter_conversation_scenarios,
    load_conversation_scenarios,
)


class TestDialogueGuidance:
    """Test DialogueGuidance Pydantic model."""

    def test_dialogue_guidance_all_fields(self):
        """DialogueGuidance can be created with all fields."""
        guidance = DialogueGuidance(
            tone_preference="professional",
            escalation_strategy="politely insist",
            factual_constraints=["Budget is $500", "Prefer morning flights"],
        )
        assert guidance.tone_preference == "professional"
        assert guidance.escalation_strategy == "politely insist"
        assert guidance.factual_constraints == ["Budget is $500", "Prefer morning flights"]

    def test_dialogue_guidance_all_fields_optional(self):
        """DialogueGuidance works with all fields optional."""
        guidance = DialogueGuidance()
        assert guidance.tone_preference is None
        assert guidance.escalation_strategy is None
        assert guidance.factual_constraints is None

    def test_dialogue_guidance_partial_fields(self):
        """DialogueGuidance works with partial fields."""
        guidance = DialogueGuidance(
            tone_preference="frustrated",
        )
        assert guidance.tone_preference == "frustrated"
        assert guidance.escalation_strategy is None
        assert guidance.factual_constraints is None

    def test_dialogue_guidance_extra_ignore(self):
        """DialogueGuidance ignores extra fields."""
        guidance = DialogueGuidance(
            tone_preference="casual",
            unknown_field="should be ignored",
        )
        assert guidance.tone_preference == "casual"
        assert not hasattr(guidance, "unknown_field")


class TestConversationScenario:
    """Test ConversationScenario Pydantic model."""

    def test_conversation_scenario_basic_creation(self):
        """ConversationScenario can be created with required fields."""
        scenario = ConversationScenario(
            scenario_id="booking_flight",
            user_goal="Book a flight from NYC to LAX",
        )
        assert scenario.scenario_id == "booking_flight"
        assert scenario.user_goal == "Book a flight from NYC to LAX"
        assert scenario.context is None
        assert scenario.dialogue_guidance is None

    def test_conversation_scenario_with_context(self):
        """ConversationScenario can be created with context."""
        scenario = ConversationScenario(
            scenario_id="booking_flight",
            user_goal="Book a flight",
            context="User is a frequent flyer with loyalty status",
        )
        assert scenario.context == "User is a frequent flyer with loyalty status"

    def test_conversation_scenario_with_dialogue_guidance(self):
        """ConversationScenario can be created with dialogue_guidance."""
        scenario = ConversationScenario(
            scenario_id="booking_flight",
            user_goal="Book a flight",
            dialogue_guidance=DialogueGuidance(
                tone_preference="professional",
                escalation_strategy="politely insist",
            ),
        )
        assert scenario.dialogue_guidance.tone_preference == "professional"
        assert scenario.dialogue_guidance.escalation_strategy == "politely insist"

    def test_conversation_scenario_with_nested_dict_guidance(self):
        """ConversationScenario accepts dialogue_guidance as dict."""
        scenario = ConversationScenario(
            scenario_id="booking_flight",
            user_goal="Book a flight",
            dialogue_guidance={
                "tone_preference": "casual",
                "factual_constraints": ["Budget is $500"],
            },
        )
        assert scenario.dialogue_guidance.tone_preference == "casual"
        assert scenario.dialogue_guidance.factual_constraints == ["Budget is $500"]

    def test_conversation_scenario_requires_scenario_id(self):
        """ConversationScenario requires scenario_id field."""
        with pytest.raises(ValidationError) as exc_info:
            ConversationScenario(user_goal="Book a flight")

        error_msg = str(exc_info.value).lower()
        assert "id" in error_msg or "scenario_id" in error_msg

    def test_conversation_scenario_requires_user_goal(self):
        """ConversationScenario requires user_goal field."""
        with pytest.raises(ValidationError) as exc_info:
            ConversationScenario(scenario_id="booking_flight")

        assert "user_goal" in str(exc_info.value).lower()

    def test_conversation_scenario_rejects_empty_user_goal(self):
        """ConversationScenario rejects empty user_goal."""
        with pytest.raises(ValidationError) as exc_info:
            ConversationScenario(
                scenario_id="booking_flight",
                user_goal="",
            )

        error_msg = str(exc_info.value)
        assert "user_goal cannot be empty" in error_msg

    def test_conversation_scenario_rejects_whitespace_user_goal(self):
        """ConversationScenario rejects whitespace-only user_goal."""
        with pytest.raises(ValidationError) as exc_info:
            ConversationScenario(
                scenario_id="booking_flight",
                user_goal="   ",
            )

        error_msg = str(exc_info.value)
        assert "user_goal cannot be empty" in error_msg

    def test_conversation_scenario_extra_ignore(self):
        """ConversationScenario ignores extra fields."""
        scenario = ConversationScenario(
            scenario_id="booking_flight",
            user_goal="Book a flight",
            extra_field="should be ignored",
        )
        assert not hasattr(scenario, "extra_field")

    def test_conversation_scenario_id_property(self):
        """ConversationScenario.id property returns scenario_id."""
        scenario = ConversationScenario(
            scenario_id="booking_flight",
            user_goal="Book a flight",
        )
        assert scenario.id == "booking_flight"

    def test_conversation_scenario_with_alias_id(self):
        """ConversationScenario can be created with 'id' field alias."""
        scenario = ConversationScenario(
            id="booking_flight",
            user_goal="Book a flight",
        )
        assert scenario.scenario_id == "booking_flight"
        assert scenario.id == "booking_flight"

    def test_conversation_scenario_full_example(self):
        """ConversationScenario with all fields populated."""
        scenario = ConversationScenario(
            id="booking_flight",
            user_goal="Book a round-trip flight from NYC to LAX for next weekend",
            context="User is a frequent flyer with airline loyalty status",
            dialogue_guidance={
                "tone_preference": "professional but time-pressed",
                "escalation_strategy": "politely insist if initial options don't meet preferences",
                "factual_constraints": ["Budget is $500 max", "Must arrive by 2pm local time"],
            },
        )
        assert scenario.id == "booking_flight"
        assert "round-trip" in scenario.user_goal
        assert "frequent flyer" in scenario.context
        assert scenario.dialogue_guidance.tone_preference == "professional but time-pressed"
        assert len(scenario.dialogue_guidance.factual_constraints) == 2


class TestLoadConversationScenarios:
    """Test load_conversation_scenarios utility function."""

    def test_load_from_json_file(self, tmp_path: Path):
        """Load scenarios from JSON file."""
        scenarios_data = [
            {"id": "scenario1", "user_goal": "Book a flight"},
            {"id": "scenario2", "user_goal": "Check order status", "context": "Order #12345"},
        ]
        file_path = tmp_path / "scenarios.json"
        file_path.write_text(json.dumps(scenarios_data))

        scenarios = load_conversation_scenarios(file_path)

        assert len(scenarios) == 2
        assert scenarios[0].id == "scenario1"
        assert scenarios[0].user_goal == "Book a flight"
        assert scenarios[1].id == "scenario2"
        assert scenarios[1].context == "Order #12345"

    def test_load_from_jsonl_file(self, tmp_path: Path):
        """Load scenarios from JSONL file."""
        scenarios_data = [
            {"id": "scenario1", "user_goal": "Book a flight"},
            {"id": "scenario2", "user_goal": "Check order status"},
        ]
        file_path = tmp_path / "scenarios.jsonl"
        file_path.write_text("\n".join(json.dumps(s) for s in scenarios_data))

        scenarios = load_conversation_scenarios(file_path)

        assert len(scenarios) == 2
        assert scenarios[0].id == "scenario1"
        assert scenarios[1].id == "scenario2"

    def test_load_empty_json_array(self, tmp_path: Path):
        """Load empty JSON array returns empty list."""
        file_path = tmp_path / "scenarios.json"
        file_path.write_text("[]")

        scenarios = load_conversation_scenarios(file_path)

        assert scenarios == []

    def test_load_empty_jsonl_file(self, tmp_path: Path):
        """Load empty JSONL file returns empty list."""
        file_path = tmp_path / "scenarios.jsonl"
        file_path.write_text("")

        scenarios = load_conversation_scenarios(file_path)

        assert scenarios == []

    def test_load_raises_filenotfound(self, tmp_path: Path):
        """Load raises FileNotFoundError for missing file."""
        file_path = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError) as exc_info:
            load_conversation_scenarios(file_path)

        assert "Scenario file not found" in str(exc_info.value)

    def test_load_raises_for_non_array_json(self, tmp_path: Path):
        """Load raises ValueError for non-array JSON."""
        file_path = tmp_path / "scenarios.json"
        file_path.write_text('{"id": "scenario1", "user_goal": "Book"}')

        with pytest.raises(ValueError) as exc_info:
            load_conversation_scenarios(file_path)

        assert "must contain an array" in str(exc_info.value)

    def test_load_raises_for_invalid_json(self, tmp_path: Path):
        """Load raises ValueError for invalid JSON."""
        file_path = tmp_path / "scenarios.jsonl"
        file_path.write_text('{"id": "scenario1", "user_goal": "Book"}\n{invalid json}')

        with pytest.raises(ValueError) as exc_info:
            load_conversation_scenarios(file_path)

        assert "Invalid JSON on line 2" in str(exc_info.value)

    def test_load_raises_for_missing_user_goal(self, tmp_path: Path):
        """Load raises ValueError when user_goal is missing."""
        scenarios_data = [
            {"id": "scenario1"},  # Missing user_goal
        ]
        file_path = tmp_path / "scenarios.json"
        file_path.write_text(json.dumps(scenarios_data))

        with pytest.raises(ValueError) as exc_info:
            load_conversation_scenarios(file_path)

        error_msg = str(exc_info.value)
        assert "validation failed for 'scenario1'" in error_msg

    def test_load_raises_for_unsupported_format(self, tmp_path: Path):
        """Load raises ValueError for unsupported file format."""
        file_path = tmp_path / "scenarios.txt"
        file_path.write_text("some text")

        with pytest.raises(ValueError) as exc_info:
            load_conversation_scenarios(file_path)

        assert "Unsupported file extension" in str(exc_info.value)

    def test_load_with_full_scenario_data(self, tmp_path: Path):
        """Load scenarios with complete data including dialogue_guidance."""
        scenarios_data = [
            {
                "id": "booking_flight",
                "user_goal": "Book a round-trip flight from NYC to LAX",
                "context": "User is a frequent flyer",
                "dialogue_guidance": {
                    "tone_preference": "professional",
                    "escalation_strategy": "politely insist",
                    "factual_constraints": ["Budget is $500"],
                },
            }
        ]
        file_path = tmp_path / "scenarios.json"
        file_path.write_text(json.dumps(scenarios_data))

        scenarios = load_conversation_scenarios(file_path)

        assert len(scenarios) == 1
        scenario = scenarios[0]
        assert scenario.id == "booking_flight"
        assert scenario.dialogue_guidance.tone_preference == "professional"
        assert scenario.dialogue_guidance.factual_constraints == ["Budget is $500"]

    def test_load_accepts_string_path(self, tmp_path: Path):
        """Load accepts string path."""
        scenarios_data = [{"id": "scenario1", "user_goal": "Test"}]
        file_path = tmp_path / "scenarios.json"
        file_path.write_text(json.dumps(scenarios_data))

        scenarios = load_conversation_scenarios(str(file_path))

        assert len(scenarios) == 1


class TestIterConversationScenarios:
    """Test iter_conversation_scenarios utility function."""

    def test_iter_from_json_file(self, tmp_path: Path):
        """Iterate scenarios from JSON file."""
        scenarios_data = [
            {"id": "scenario1", "user_goal": "Book a flight"},
            {"id": "scenario2", "user_goal": "Check order status"},
        ]
        file_path = tmp_path / "scenarios.json"
        file_path.write_text(json.dumps(scenarios_data))

        scenarios = list(iter_conversation_scenarios(file_path))

        assert len(scenarios) == 2
        assert scenarios[0].id == "scenario1"
        assert scenarios[1].id == "scenario2"

    def test_iter_from_jsonl_file(self, tmp_path: Path):
        """Iterate scenarios from JSONL file (memory efficient)."""
        scenarios_data = [
            {"id": "scenario1", "user_goal": "Book a flight"},
            {"id": "scenario2", "user_goal": "Check order status"},
        ]
        file_path = tmp_path / "scenarios.jsonl"
        file_path.write_text("\n".join(json.dumps(s) for s in scenarios_data))

        # Test that it's actually an iterator
        iterator = iter_conversation_scenarios(file_path)
        assert hasattr(iterator, "__next__")

        scenarios = list(iterator)
        assert len(scenarios) == 2

    def test_iter_raises_filenotfound(self, tmp_path: Path):
        """Iter raises FileNotFoundError for missing file."""
        file_path = tmp_path / "nonexistent.jsonl"

        with pytest.raises(FileNotFoundError):
            list(iter_conversation_scenarios(file_path))

    def test_iter_handles_empty_lines_in_jsonl(self, tmp_path: Path):
        """Iter skips empty lines in JSONL."""
        file_path = tmp_path / "scenarios.jsonl"
        file_path.write_text(
            '{"id": "scenario1", "user_goal": "Test1"}\n'
            "\n"
            '{"id": "scenario2", "user_goal": "Test2"}\n'
            "   \n"
        )

        scenarios = list(iter_conversation_scenarios(file_path))

        assert len(scenarios) == 2

    def test_iter_raises_for_invalid_scenario(self, tmp_path: Path):
        """Iter raises ValueError for invalid scenario in JSONL."""
        file_path = tmp_path / "scenarios.jsonl"
        file_path.write_text(
            '{"id": "scenario1", "user_goal": "Valid"}\n{"id": "scenario2"}\n'  # Missing user_goal
        )

        with pytest.raises(ValueError) as exc_info:
            list(iter_conversation_scenarios(file_path))

        assert "validation failed" in str(exc_info.value)


class TestModelExports:
    """Test that models are properly exported from gavel_ai.models package."""

    def test_conversation_scenario_exported(self):
        """ConversationScenario is exported from gavel_ai.models."""
        from gavel_ai.models import ConversationScenario as ExportedModel

        assert ExportedModel is ConversationScenario

    def test_dialogue_guidance_exported(self):
        """DialogueGuidance is exported from gavel_ai.models."""
        from gavel_ai.models import DialogueGuidance as ExportedModel

        assert ExportedModel is DialogueGuidance

    def test_load_function_exported(self):
        """load_conversation_scenarios is exported from gavel_ai.models."""
        from gavel_ai.models import load_conversation_scenarios as ExportedFunc

        assert ExportedFunc is load_conversation_scenarios

    def test_iter_function_exported(self):
        """iter_conversation_scenarios is exported from gavel_ai.models."""
        from gavel_ai.models import iter_conversation_scenarios as ExportedFunc

        assert ExportedFunc is iter_conversation_scenarios

    def test_turn_exported(self):
        """Turn is exported from gavel_ai.models."""
        from gavel_ai.models import Turn as ExportedModel

        assert ExportedModel is Turn

    def test_turn_metadata_exported(self):
        """TurnMetadata is exported from gavel_ai.models."""
        from gavel_ai.models import TurnMetadata as ExportedModel

        assert ExportedModel is TurnMetadata

    def test_conversation_state_exported(self):
        """ConversationState is exported from gavel_ai.models."""
        from gavel_ai.models import ConversationState as ExportedModel

        assert ExportedModel is ConversationState


class TestTurnMetadata:
    """Test TurnMetadata Pydantic model."""

    def test_turn_metadata_all_fields(self):
        """TurnMetadata can be created with all fields."""
        metadata = TurnMetadata(
            tokens_prompt=150,
            tokens_completion=100,
            latency_ms=2500,
            extra={"model": "claude-3.5-sonnet"},
        )
        assert metadata.tokens_prompt == 150
        assert metadata.tokens_completion == 100
        assert metadata.latency_ms == 2500
        assert metadata.extra == {"model": "claude-3.5-sonnet"}

    def test_turn_metadata_all_fields_optional(self):
        """TurnMetadata works with all fields optional."""
        metadata = TurnMetadata()
        assert metadata.tokens_prompt is None
        assert metadata.tokens_completion is None
        assert metadata.latency_ms is None
        assert metadata.extra is None

    def test_turn_metadata_partial_fields(self):
        """TurnMetadata works with partial fields."""
        metadata = TurnMetadata(latency_ms=500)
        assert metadata.tokens_prompt is None
        assert metadata.tokens_completion is None
        assert metadata.latency_ms == 500
        assert metadata.extra is None

    def test_turn_metadata_extra_ignore(self):
        """TurnMetadata ignores extra fields."""
        metadata = TurnMetadata(
            tokens_prompt=100,
            unknown_field="should be ignored",
        )
        assert metadata.tokens_prompt == 100
        assert not hasattr(metadata, "unknown_field")


class TestTurn:
    """Test Turn Pydantic model."""

    def test_turn_all_fields(self):
        """Turn can be created with all fields."""
        now = datetime.now(UTC)
        metadata = TurnMetadata(latency_ms=100)
        turn = Turn(
            turn_number=0,
            role="user",
            content="Hello, world!",
            timestamp=now,
            metadata=metadata,
        )
        assert turn.turn_number == 0
        assert turn.role == "user"
        assert turn.content == "Hello, world!"
        assert turn.timestamp == now
        assert turn.metadata.latency_ms == 100

    def test_turn_required_fields_only(self):
        """Turn can be created with only required fields."""
        turn = Turn(
            turn_number=0,
            role="assistant",
            content="How can I help you?",
        )
        assert turn.turn_number == 0
        assert turn.role == "assistant"
        assert turn.content == "How can I help you?"
        assert turn.timestamp is not None  # Has default
        assert turn.metadata is None

    def test_turn_role_user(self):
        """Turn accepts 'user' role."""
        turn = Turn(turn_number=0, role="user", content="Test")
        assert turn.role == "user"

    def test_turn_role_assistant(self):
        """Turn accepts 'assistant' role."""
        turn = Turn(turn_number=0, role="assistant", content="Test")
        assert turn.role == "assistant"

    def test_turn_rejects_invalid_role(self):
        """Turn rejects invalid role values."""
        with pytest.raises(ValidationError) as exc_info:
            Turn(turn_number=0, role="system", content="Test")

        error_msg = str(exc_info.value).lower()
        assert "role" in error_msg or "input should be" in error_msg

    def test_turn_rejects_empty_content(self):
        """Turn rejects empty content."""
        with pytest.raises(ValidationError) as exc_info:
            Turn(turn_number=0, role="user", content="")

        error_msg = str(exc_info.value).lower()
        assert "content" in error_msg or "string" in error_msg

    def test_turn_rejects_negative_turn_number(self):
        """Turn rejects negative turn_number."""
        with pytest.raises(ValidationError) as exc_info:
            Turn(turn_number=-1, role="user", content="Test")

        error_msg = str(exc_info.value).lower()
        assert "turn_number" in error_msg or "greater than" in error_msg

    def test_turn_timestamp_default(self):
        """Turn has default timestamp factory."""
        before = datetime.now(UTC)
        turn = Turn(turn_number=0, role="user", content="Test")
        after = datetime.now(UTC)

        assert before <= turn.timestamp <= after

    def test_turn_extra_ignore(self):
        """Turn ignores extra fields."""
        turn = Turn(
            turn_number=0,
            role="user",
            content="Test",
            unknown_field="should be ignored",
        )
        assert not hasattr(turn, "unknown_field")

    def test_turn_with_metadata_dict(self):
        """Turn accepts metadata as dict."""
        turn = Turn(
            turn_number=0,
            role="user",
            content="Test",
            metadata={"tokens_prompt": 50, "latency_ms": 200},
        )
        assert turn.metadata.tokens_prompt == 50
        assert turn.metadata.latency_ms == 200


class TestConversationState:
    """Test ConversationState Pydantic model."""

    def test_conversation_state_basic_creation(self):
        """ConversationState can be created with required fields."""
        state = ConversationState(
            scenario_id="booking_flight",
            variant_id="claude-3.5-sonnet",
        )
        assert state.scenario_id == "booking_flight"
        assert state.variant_id == "claude-3.5-sonnet"
        assert state.turns == []
        assert state.start_time is not None
        assert state.metadata is None

    def test_conversation_state_with_metadata(self):
        """ConversationState can be created with metadata."""
        state = ConversationState(
            scenario_id="booking_flight",
            variant_id="claude-3.5-sonnet",
            metadata={"run_id": "run-123", "test_mode": True},
        )
        assert state.metadata == {"run_id": "run-123", "test_mode": True}

    def test_conversation_state_start_time_default(self):
        """ConversationState has default start_time factory."""
        before = datetime.now(UTC)
        state = ConversationState(
            scenario_id="test",
            variant_id="test",
        )
        after = datetime.now(UTC)

        assert before <= state.start_time <= after

    def test_conversation_state_requires_scenario_id(self):
        """ConversationState requires scenario_id."""
        with pytest.raises(ValidationError) as exc_info:
            ConversationState(variant_id="claude-3.5-sonnet")

        error_msg = str(exc_info.value).lower()
        assert "scenario_id" in error_msg

    def test_conversation_state_requires_variant_id(self):
        """ConversationState requires variant_id."""
        with pytest.raises(ValidationError) as exc_info:
            ConversationState(scenario_id="booking_flight")

        error_msg = str(exc_info.value).lower()
        assert "variant_id" in error_msg

    def test_conversation_state_extra_ignore(self):
        """ConversationState ignores extra fields."""
        state = ConversationState(
            scenario_id="test",
            variant_id="test",
            unknown_field="should be ignored",
        )
        assert not hasattr(state, "unknown_field")


class TestConversationStateAddTurn:
    """Test ConversationState.add_turn method."""

    def test_add_turn_basic(self):
        """add_turn adds a turn to the conversation."""
        state = ConversationState(
            scenario_id="test",
            variant_id="test",
        )

        turn = state.add_turn("user", "Hello!")

        assert len(state.turns) == 1
        assert turn.turn_number == 0
        assert turn.role == "user"
        assert turn.content == "Hello!"

    def test_add_turn_auto_increments_turn_number(self):
        """add_turn auto-increments turn_number."""
        state = ConversationState(
            scenario_id="test",
            variant_id="test",
        )

        turn1 = state.add_turn("user", "First message")
        turn2 = state.add_turn("assistant", "Second message")
        turn3 = state.add_turn("user", "Third message")

        assert turn1.turn_number == 0
        assert turn2.turn_number == 1
        assert turn3.turn_number == 2

    def test_add_turn_sets_timestamp(self):
        """add_turn sets timestamp to current UTC time."""
        state = ConversationState(
            scenario_id="test",
            variant_id="test",
        )

        before = datetime.now(UTC)
        turn = state.add_turn("user", "Test message")
        after = datetime.now(UTC)

        assert before <= turn.timestamp <= after

    def test_add_turn_with_metadata(self):
        """add_turn accepts optional metadata."""
        state = ConversationState(
            scenario_id="test",
            variant_id="test",
        )
        metadata = TurnMetadata(tokens_prompt=100, latency_ms=500)

        turn = state.add_turn("assistant", "Response", metadata=metadata)

        assert turn.metadata.tokens_prompt == 100
        assert turn.metadata.latency_ms == 500

    def test_add_turn_returns_turn(self):
        """add_turn returns the created Turn object."""
        state = ConversationState(
            scenario_id="test",
            variant_id="test",
        )

        turn = state.add_turn("user", "Hello!")

        assert isinstance(turn, Turn)
        assert turn is state.turns[0]

    def test_add_turn_appends_to_list(self):
        """add_turn appends turns to the list."""
        state = ConversationState(
            scenario_id="test",
            variant_id="test",
        )

        state.add_turn("user", "First")
        state.add_turn("assistant", "Second")
        state.add_turn("user", "Third")

        assert len(state.turns) == 3
        assert state.turns[0].content == "First"
        assert state.turns[1].content == "Second"
        assert state.turns[2].content == "Third"


class TestConversationStateHistory:
    """Test ConversationState.history property."""

    def test_history_empty_turns(self):
        """history returns empty string for empty turns."""
        state = ConversationState(
            scenario_id="test",
            variant_id="test",
        )

        assert state.history == ""

    def test_history_single_turn(self):
        """history formats single turn correctly."""
        state = ConversationState(
            scenario_id="test",
            variant_id="test",
        )
        state.add_turn("user", "Hello")

        assert state.history == "user: Hello"

    def test_history_multiple_turns(self):
        """history formats multiple turns correctly."""
        state = ConversationState(
            scenario_id="test",
            variant_id="test",
        )
        state.add_turn("user", "I want to book a flight")
        state.add_turn("assistant", "I'd be happy to help. Where would you like to go?")
        state.add_turn("user", "NYC to LAX")

        expected = (
            "user: I want to book a flight\n"
            "assistant: I'd be happy to help. Where would you like to go?\n"
            "user: NYC to LAX"
        )
        assert state.history == expected

    def test_history_preserves_content(self):
        """history preserves turn content exactly."""
        state = ConversationState(
            scenario_id="test",
            variant_id="test",
        )
        state.add_turn("user", "Message with: colon")
        state.add_turn("assistant", "Response with\nnewline")

        history = state.history
        assert "Message with: colon" in history
        assert "Response with\nnewline" in history


class TestConversationStateFullExample:
    """Integration tests for ConversationState with realistic usage."""

    def test_full_conversation_workflow(self):
        """Test complete conversation workflow from Dev Notes example."""
        # Create conversation state
        state = ConversationState(
            scenario_id="booking_flight",
            variant_id="claude-3.5-sonnet",
        )

        # Add turns
        state.add_turn("user", "I want to book a flight to NYC")
        state.add_turn(
            "assistant",
            "I'd be happy to help you book a flight to NYC. What dates are you looking at?",
        )
        state.add_turn(
            "user",
            "Next weekend, departing Friday",
            metadata=TurnMetadata(latency_ms=150),
        )

        # Verify state
        assert state.scenario_id == "booking_flight"
        assert state.variant_id == "claude-3.5-sonnet"
        assert len(state.turns) == 3

        # Verify turn numbers
        assert state.turns[0].turn_number == 0
        assert state.turns[1].turn_number == 1
        assert state.turns[2].turn_number == 2

        # Verify roles
        assert state.turns[0].role == "user"
        assert state.turns[1].role == "assistant"
        assert state.turns[2].role == "user"

        # Verify metadata on third turn
        assert state.turns[2].metadata.latency_ms == 150

        # Verify history formatting
        expected_history = (
            "user: I want to book a flight to NYC\n"
            "assistant: I'd be happy to help you book a flight to NYC. What dates are you looking at?\n"
            "user: Next weekend, departing Friday"
        )
        assert state.history == expected_history


class TestTurnResult:
    """Test TurnResult Pydantic model."""

    def test_turn_result_creation_all_fields(self):
        """TurnResult can be created with all fields."""
        result = TurnResult(
            turn_number=1,
            processor_output="Response",
            latency_ms=100,
            tokens_prompt=50,
            tokens_completion=20,
            error="Something went wrong",
        )
        assert result.turn_number == 1
        assert result.processor_output == "Response"
        assert result.latency_ms == 100
        assert result.tokens_prompt == 50
        assert result.tokens_completion == 20
        assert result.error == "Something went wrong"

    def test_turn_result_optional_fields(self):
        """TurnResult checks optional fields."""
        result = TurnResult(
            turn_number=0,
            processor_output="Hello",
            latency_ms=50,
        )
        assert result.tokens_prompt is None
        assert result.tokens_completion is None
        assert result.error is None


class TestConversationResult:
    """Test ConversationResult Pydantic model."""

    def test_conversation_result_creation_all_fields(self):
        """ConversationResult can be created with all fields."""
        transcript = ConversationState(scenario_id="s1", variant_id="v1")
        result = ConversationResult(
            scenario_id="s1",
            variant_id="v1",
            conversation_transcript=transcript,
            duration_ms=1000,
            completed=True,
            tokens_total=100,
        )
        assert result.scenario_id == "s1"
        assert result.variant_id == "v1"
        assert result.conversation_transcript == transcript
        assert result.duration_ms == 1000
        assert result.completed is True
        assert result.tokens_total == 100

    def test_total_turns_property(self):
        """total_turns property returns correct count."""
        transcript = ConversationState(scenario_id="s1", variant_id="v1")
        transcript.add_turn("user", "Hello")
        transcript.add_turn("assistant", "Hi")

        result = ConversationResult(
            scenario_id="s1",
            variant_id="v1",
            conversation_transcript=transcript,
            duration_ms=100,
        )
        assert result.total_turns == 2

    def test_compute_tokens_total(self):
        """compute_tokens_total correctly sums tokens from TurnResults."""
        transcript = ConversationState(scenario_id="s1", variant_id="v1")

        turn_results = [
            TurnResult(
                turn_number=0,
                processor_output="",
                latency_ms=0,
                tokens_prompt=10,
                tokens_completion=5,
            ),
            TurnResult(
                turn_number=1,
                processor_output="",
                latency_ms=0,
                tokens_prompt=20,
                tokens_completion=10,
            ),
        ]

        result = ConversationResult(
            scenario_id="s1",
            variant_id="v1",
            conversation_transcript=transcript,
            results_raw=turn_results,
            duration_ms=100,
        )
        assert result.compute_tokens_total() == 45  # 10+5+20+10

    def test_to_jsonl_entry(self):
        """to_jsonl_entry serialized correctly."""
        transcript = ConversationState(scenario_id="s1", variant_id="v1")
        result = ConversationResult(
            scenario_id="s1",
            variant_id="v1",
            conversation_transcript=transcript,
            duration_ms=100,
        )
        entry = result.to_jsonl_entry()
        assert isinstance(entry, dict)
        assert entry["scenario_id"] == "s1"
        assert entry["metadata"]["duration_ms"] == 100
