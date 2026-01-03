"""Unit tests for scenarios configuration."""
import csv
import json
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

from gavel_ai.core.config.scenarios import (
    Scenario,
    ScenarioSet,
    load_scenarios,
    load_scenarios_csv,
    load_scenarios_json,
    process_scenario_input,
    substitute_placeholders,
)
from gavel_ai.core.exceptions import ConfigError, ValidationError


class TestScenarioModel:
    """Test suite for Scenario Pydantic model."""

    def test_parse_basic_scenario(self) -> None:
        """Test parsing a basic scenario with required fields."""
        scenario_data: Dict[str, Any] = {
            "id": "scenario-1",
            "input": {"user_input": "What is 2+2?"},
        }

        scenario = Scenario.model_validate(scenario_data)

        assert scenario.id == "scenario-1"
        # Input is converted from dict to string
        assert scenario.input == "What is 2+2?"
        assert scenario.expected_behavior is None

    def test_parse_scenario_with_expected_behavior(self) -> None:
        """Test parsing scenario with expected behavior."""
        scenario_data: Dict[str, Any] = {
            "id": "scenario-1",
            "input": {"user_input": "What is the capital of France?"},
            "expected_behavior": "Should answer 'Paris'",
        }

        scenario = Scenario.model_validate(scenario_data)

        assert scenario.expected_behavior == "Should answer 'Paris'"

    def test_parse_scenario_with_metadata(self) -> None:
        """Test parsing scenario with metadata."""
        scenario_data: Dict[str, Any] = {
            "id": "scenario-1",
            "input": {"user_input": "Test"},
            "metadata": {"category": "geography", "difficulty": "easy"},
        }

        scenario = Scenario.model_validate(scenario_data)

        assert scenario.metadata == {"category": "geography", "difficulty": "easy"}

    def test_scenario_has_extra_ignore(self) -> None:
        """Test that Scenario ignores unknown fields."""
        scenario_data: Dict[str, Any] = {
            "id": "scenario-1",
            "input": {"user_input": "Test"},
            "future_field": "ignored",
        }

        scenario = Scenario.model_validate(scenario_data)

        assert scenario.id == "scenario-1"
        assert not hasattr(scenario, "future_field")


class TestScenarioSetModel:
    """Test suite for ScenarioSet Pydantic model."""

    def test_parse_scenario_set(self) -> None:
        """Test parsing scenario set with multiple scenarios."""
        data: Dict[str, Any] = {
            "scenarios": [
                {"id": "scenario-1", "input": {"user_input": "Test 1"}},
                {"id": "scenario-2", "input": {"user_input": "Test 2"}},
            ]
        }

        scenario_set = ScenarioSet.model_validate(data)

        assert len(scenario_set.scenarios) == 2
        assert scenario_set.scenarios[0].id == "scenario-1"
        assert scenario_set.scenarios[1].id == "scenario-2"


class TestJSONLoader:
    """Test suite for JSON scenarios loader."""

    def test_load_scenarios_json(self, tmp_path: Path) -> None:
        """Test loading scenarios from JSON file."""
        scenarios_data: Dict[str, Any] = {
            "scenarios": [
                {
                    "id": "scenario-1",
                    "input": {"user_input": "What is the capital of France?"},
                    "expected_behavior": "Paris",
                },
                {
                    "id": "scenario-2",
                    "input": {"user_input": "Explain quantum computing"},
                },
            ]
        }

        scenarios_file = tmp_path / "scenarios.json"
        with open(scenarios_file, "w") as f:
            json.dump(scenarios_data, f)

        scenarios = load_scenarios_json(scenarios_file)

        assert len(scenarios) == 2
        assert scenarios[0].id == "scenario-1"
        assert scenarios[1].id == "scenario-2"

    def test_load_scenarios_json_missing_file(self, tmp_path: Path) -> None:
        """Test that ConfigError is raised for missing JSON file."""
        scenarios_file = tmp_path / "nonexistent.json"

        with pytest.raises(ConfigError) as exc_info:
            load_scenarios_json(scenarios_file)

        assert "not found" in str(exc_info.value).lower()


class TestCSVLoader:
    """Test suite for CSV scenarios loader."""

    def test_load_scenarios_csv(self, tmp_path: Path) -> None:
        """Test loading scenarios from CSV file."""
        scenarios_file = tmp_path / "scenarios.csv"
        with open(scenarios_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["scenario_id", "input", "expected"]
            )
            writer.writerow(
                ["scenario-1", "What is the capital of France?", "Paris"]
            )
            writer.writerow(
                ["scenario-2", "Explain quantum computing", ""]
            )

        scenarios = load_scenarios_csv(scenarios_file)

        assert len(scenarios) == 2
        assert scenarios[0].id == "scenario-1"
        # Input is converted from CSV string to Scenario input field
        assert scenarios[0].input == "What is the capital of France?"
        assert scenarios[0].expected == "Paris"

    def test_load_scenarios_csv_alternate_id_column(self, tmp_path: Path) -> None:
        """Test CSV with 'id' column instead of 'scenario_id'."""
        scenarios_file = tmp_path / "scenarios.csv"
        with open(scenarios_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "input"])
            writer.writerow(["scenario-1", "Test input"])

        scenarios = load_scenarios_csv(scenarios_file)

        assert len(scenarios) == 1
        assert scenarios[0].id == "scenario-1"
        assert scenarios[0].input == "Test input"

    def test_load_scenarios_csv_missing_id_raises_error(self, tmp_path: Path) -> None:
        """Test that ValidationError is raised when CSV has no id column."""
        scenarios_file = tmp_path / "scenarios.csv"
        with open(scenarios_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["user_input"])
            writer.writerow(["Test"])

        with pytest.raises(ValidationError) as exc_info:
            load_scenarios_csv(scenarios_file)

        error_msg = str(exc_info.value)
        assert "scenario_id" in error_msg.lower() or "id" in error_msg.lower()

    def test_load_scenarios_csv_missing_file(self, tmp_path: Path) -> None:
        """Test that ConfigError is raised for missing CSV file."""
        scenarios_file = tmp_path / "nonexistent.csv"

        with pytest.raises(ConfigError) as exc_info:
            load_scenarios_csv(scenarios_file)

        assert "not found" in str(exc_info.value).lower()


class TestAutoDetection:
    """Test suite for auto-detection of format."""

    def test_load_scenarios_detects_json(self, tmp_path: Path) -> None:
        """Test that load_scenarios auto-detects JSON format."""
        scenarios_data: Dict[str, Any] = {
            "scenarios": [{"id": "scenario-1", "input": {"user_input": "Test"}}]
        }

        scenarios_file = tmp_path / "scenarios.json"
        with open(scenarios_file, "w") as f:
            json.dump(scenarios_data, f)

        scenarios = load_scenarios(scenarios_file)

        assert len(scenarios) == 1
        assert scenarios[0].id == "scenario-1"

    def test_load_scenarios_detects_csv(self, tmp_path: Path) -> None:
        """Test that load_scenarios auto-detects CSV format."""
        scenarios_file = tmp_path / "scenarios.csv"
        with open(scenarios_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["scenario_id", "input"])
            writer.writerow(["scenario-1", "Test"])

        scenarios = load_scenarios(scenarios_file)

        assert len(scenarios) == 1
        assert scenarios[0].id == "scenario-1"

    def test_load_scenarios_unsupported_format(self, tmp_path: Path) -> None:
        """Test that ConfigError is raised for unsupported format."""
        scenarios_file = tmp_path / "scenarios.xml"
        scenarios_file.write_text("<scenarios></scenarios>")

        with pytest.raises(ConfigError) as exc_info:
            load_scenarios(scenarios_file)

        error_msg = str(exc_info.value)
        assert "unsupported" in error_msg.lower() or "format" in error_msg.lower()


class TestPlaceholderSubstitution:
    """Test suite for placeholder substitution."""

    def test_substitute_placeholders_basic(self) -> None:
        """Test basic placeholder substitution."""
        template = "Translate '{{text}}' to French"
        data = {"text": "Hello world"}

        result = substitute_placeholders(template, data)

        assert result == "Translate 'Hello world' to French"

    def test_substitute_placeholders_multiple(self) -> None:
        """Test substitution with multiple placeholders."""
        template = "{{name}} is {{age}} years old"
        data = {"name": "Alice", "age": "30"}

        result = substitute_placeholders(template, data)

        assert result == "Alice is 30 years old"

    def test_substitute_placeholders_missing_field(self) -> None:
        """Test that ValidationError is raised for missing placeholder field."""
        template = "Hello {{name}}"
        data = {}  # Missing 'name'

        with pytest.raises(ValidationError) as exc_info:
            substitute_placeholders(template, data)

        assert "name" in str(exc_info.value)

    def test_process_scenario_input(self) -> None:
        """Test processing scenario input with placeholders."""
        # For placeholders to work with string input, we need to use scenario metadata
        scenario = Scenario.model_validate(
            {
                "id": "scenario-1",
                "input": "Translate '{{text}}' to French",
                "metadata": {"text": "Hello world"},
            }
        )

        processed = process_scenario_input(scenario)

        assert processed == "Translate 'Hello world' to French"

    def test_process_scenario_input_no_placeholders(self) -> None:
        """Test processing scenario input without placeholders."""
        scenario = Scenario.model_validate(
            {"id": "scenario-1", "input": {"user_input": "Simple text"}}
        )

        processed = process_scenario_input(scenario)

        # Input dict gets converted to string "Simple text"
        assert processed == "Simple text"


class TestPerformance:
    """Test suite for performance requirements."""

    def test_load_100_scenarios_performance(self, tmp_path: Path) -> None:
        """Test that 100 scenarios load in <100ms."""
        # Generate 100 scenarios
        scenarios_data: Dict[str, Any] = {
            "scenarios": [
                {"id": f"scenario-{i}", "input": {"user_input": f"Test input {i}"}}
                for i in range(100)
            ]
        }

        scenarios_file = tmp_path / "scenarios.json"
        with open(scenarios_file, "w") as f:
            json.dump(scenarios_data, f)

        # Measure loading time
        start = time.time()
        scenarios = load_scenarios_json(scenarios_file)
        elapsed = time.time() - start

        assert len(scenarios) == 100
        assert elapsed < 0.1  # <100ms

    def test_load_1000_scenarios_performance(self, tmp_path: Path) -> None:
        """Test that 1000 scenarios load in <1s."""
        # Generate 1000 scenarios
        scenarios_data: Dict[str, Any] = {
            "scenarios": [
                {"id": f"scenario-{i}", "input": {"user_input": f"Test input {i}"}}
                for i in range(1000)
            ]
        }

        scenarios_file = tmp_path / "scenarios.json"
        with open(scenarios_file, "w") as f:
            json.dump(scenarios_data, f)

        # Measure loading time
        start = time.time()
        scenarios = load_scenarios_json(scenarios_file)
        elapsed = time.time() - start

        assert len(scenarios) == 1000
        assert elapsed < 1.0  # <1s
