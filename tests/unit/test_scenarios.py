"""
Unit tests for Scenario model.
"""

import json

import pytest
from pydantic import ValidationError

from gavel_ai.models.scenarios import Scenario


class TestScenarioModel:
    """Test Scenario Pydantic model."""

    def test_scenario_basic_creation(self):
        """Scenario can be created with required fields."""
        scenario = Scenario(
            scenario_id="test-1",
            input="What is the capital of France?",
        )
        assert scenario.scenario_id == "test-1"
        assert scenario.input == "What is the capital of France?"
        assert scenario.expected is None
        assert scenario.metadata is None

    def test_scenario_with_expected(self):
        """Scenario can be created with expected field."""
        scenario = Scenario(
            scenario_id="test-1",
            input="Question",
            expected="Paris",
        )
        assert scenario.expected == "Paris"

    def test_scenario_with_metadata(self):
        """Scenario can be created with metadata."""
        scenario = Scenario(
            scenario_id="test-1",
            input="Question",
            metadata={"category": "geography", "difficulty": "easy"},
        )
        assert scenario.metadata["category"] == "geography"
        assert scenario.metadata["difficulty"] == "easy"

    def test_scenario_requires_scenario_id(self):
        """Scenario requires scenario_id field."""
        with pytest.raises(ValidationError) as exc_info:
            Scenario(input="Question")

        error_msg = str(exc_info.value).lower()
        assert "id" in error_msg or "scenario_id" in error_msg

    def test_scenario_requires_input(self):
        """Scenario requires input field."""
        with pytest.raises(ValidationError) as exc_info:
            Scenario(scenario_id="test-1")

        assert "input" in str(exc_info.value)

    def test_scenario_input_with_dict_user_input(self):
        """Scenario converts dict with 'user_input' to string."""
        scenario = Scenario(
            scenario_id="test-1",
            input={"user_input": "What is the capital?"},
        )
        assert scenario.input == "What is the capital?"

    def test_scenario_input_with_dict_input(self):
        """Scenario converts dict with 'input' to string."""
        scenario = Scenario(
            scenario_id="test-1",
            input={"input": "Test question"},
        )
        assert scenario.input == "Test question"

    def test_scenario_input_with_dict_prompt(self):
        """Scenario converts dict with 'prompt' to string."""
        scenario = Scenario(
            scenario_id="test-1",
            input={"prompt": "Test prompt"},
        )
        assert scenario.input == "Test prompt"

    def test_scenario_input_with_dict_fallback_to_json(self):
        """Scenario converts dict to JSON string when no known key."""
        input_dict = {"custom_key": "custom_value", "another": "value"}
        scenario = Scenario(
            scenario_id="test-1",
            input=input_dict,
        )
        assert scenario.input == json.dumps(input_dict)

    def test_scenario_input_with_non_dict_converts_to_string(self):
        """Scenario converts non-dict input to string."""
        scenario = Scenario(
            scenario_id="test-1",
            input=123,
        )
        assert scenario.input == "123"

    def test_scenario_extra_ignore(self):
        """Scenario ignores extra fields."""
        scenario = Scenario(
            scenario_id="test-1",
            input="Question",
            extra_field="should be ignored",
        )
        assert not hasattr(scenario, "extra_field")

    def test_scenario_id_property(self):
        """Scenario.id property returns scenario_id."""
        scenario = Scenario(
            scenario_id="test-1",
            input="Question",
        )
        assert scenario.id == "test-1"

    def test_scenario_expected_behavior_property(self):
        """Scenario.expected_behavior property returns expected."""
        scenario = Scenario(
            scenario_id="test-1",
            input="Question",
            expected="Expected answer",
        )
        assert scenario.expected_behavior == "Expected answer"

    def test_scenario_with_alias_id(self):
        """Scenario can be created with 'id' field alias."""
        scenario = Scenario(
            id="test-1",
            input="Question",
        )
        assert scenario.scenario_id == "test-1"

    def test_scenario_with_alias_expected_behavior(self):
        """Scenario can be created with 'expected_behavior' field alias."""
        scenario = Scenario(
            scenario_id="test-1",
            input="Question",
            expected_behavior="Expected answer",
        )
        assert scenario.expected == "Expected answer"

    def test_scenario_complex_dict_input(self):
        """Scenario handles complex nested dict input."""
        input_dict = {
            "context": "You are a helpful assistant",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ],
        }
        scenario = Scenario(
            scenario_id="test-1",
            input=input_dict,
        )
        assert isinstance(scenario.input, str)

    def test_scenario_expected_optional(self):
        """Scenario.expected is optional."""
        scenario = Scenario(
            scenario_id="test-1",
            input="Question",
        )
        assert scenario.expected is None

    def test_scenario_metadata_optional(self):
        """Scenario.metadata is optional."""
        scenario = Scenario(
            scenario_id="test-1",
            input="Question",
        )
        assert scenario.metadata is None

    def test_scenario_with_both_aliases(self):
        """Scenario can be created with both field aliases."""
        scenario = Scenario(
            id="test-1",
            input="Question",
            expected_behavior="Expected",
        )
        assert scenario.scenario_id == "test-1"
        assert scenario.expected == "Expected"
        assert scenario.id == "test-1"
        assert scenario.expected_behavior == "Expected"
