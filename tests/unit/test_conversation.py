"""
Unit tests for ConversationScenario model and loading utilities.
"""

import json
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from gavel_ai.models.conversation import (
    ConversationScenario,
    DialogueGuidance,
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

        assert "Unsupported file format" in str(exc_info.value)

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
            '{"id": "scenario1", "user_goal": "Valid"}\n'
            '{"id": "scenario2"}\n'  # Missing user_goal
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
