"""Unit tests for scenarios configuration and loading."""

import csv
import json
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

from gavel_ai.core.adapters.backends import LocalStorageBackend
from gavel_ai.core.adapters.data_sources import RecordDataSource
from gavel_ai.models.runtime import Scenario


class TestScenarioModel:
    """Test suite for Scenario Pydantic model."""

    def test_parse_basic_scenario(self) -> None:
        """Test parsing a basic scenario with required fields."""
        scenario_data: Dict[str, Any] = {
            "scenario_id": "scenario-1",
            "input": "What is 2+2?",
        }

        scenario = Scenario.model_validate(scenario_data)

        assert scenario.scenario_id == "scenario-1"
        assert scenario.input == "What is 2+2?"
        assert scenario.expected is None

    def test_parse_scenario_with_expected(self) -> None:
        """Test parsing scenario with expected output."""
        scenario_data: Dict[str, Any] = {
            "scenario_id": "scenario-1",
            "input": "What is the capital of France?",
            "expected": "Paris",
        }

        scenario = Scenario.model_validate(scenario_data)

        assert scenario.expected == "Paris"

    def test_parse_scenario_with_metadata(self) -> None:
        """Test parsing scenario with metadata."""
        scenario_data: Dict[str, Any] = {
            "scenario_id": "scenario-1",
            "input": "Test",
            "metadata": {"category": "geography", "difficulty": "easy"},
        }

        scenario = Scenario.model_validate(scenario_data)

        assert scenario.metadata == {"category": "geography", "difficulty": "easy"}

    def test_scenario_with_context(self) -> None:
        """Test parsing scenario with context."""
        scenario_data: Dict[str, Any] = {
            "scenario_id": "scenario-1",
            "input": "Test",
            "context": "Additional context for the scenario",
        }

        scenario = Scenario.model_validate(scenario_data)

        assert scenario.context == "Additional context for the scenario"


class TestJSONScenariosLoading:
    """Test suite for JSON scenarios loading via RecordDataSource."""

    def test_load_scenarios_json_array(self, tmp_path: Path) -> None:
        """Test loading scenarios from JSON array file."""
        scenarios_data: List[Dict[str, Any]] = [
            {
                "scenario_id": "scenario-1",
                "input": "What is the capital of France?",
                "expected": "Paris",
            },
            {
                "scenario_id": "scenario-2",
                "input": "Explain quantum computing",
            },
        ]

        scenarios_file = tmp_path / "scenarios.json"
        with open(scenarios_file, "w") as f:
            json.dump(scenarios_data, f)

        storage = LocalStorageBackend(tmp_path)
        source = RecordDataSource(storage, "scenarios.json", schema=Scenario)
        scenarios = source.read()

        assert len(scenarios) == 2
        assert scenarios[0].scenario_id == "scenario-1"
        assert scenarios[1].scenario_id == "scenario-2"

    def test_load_scenarios_jsonl(self, tmp_path: Path) -> None:
        """Test loading scenarios from JSONL file."""
        scenarios_file = tmp_path / "scenarios.jsonl"
        with open(scenarios_file, "w") as f:
            f.write('{"scenario_id": "s1", "input": "Test 1"}\n')
            f.write('{"scenario_id": "s2", "input": "Test 2"}\n')

        storage = LocalStorageBackend(tmp_path)
        source = RecordDataSource(storage, "scenarios.jsonl", schema=Scenario)
        scenarios = source.read()

        assert len(scenarios) == 2
        assert scenarios[0].scenario_id == "s1"
        assert scenarios[1].scenario_id == "s2"

    def test_load_scenarios_missing_file(self, tmp_path: Path) -> None:
        """Test that reading from missing file returns empty list."""
        storage = LocalStorageBackend(tmp_path)
        source = RecordDataSource(storage, "nonexistent.jsonl", schema=Scenario)

        # RecordDataSource.read() returns empty list for missing file
        scenarios = source.read()
        assert scenarios == []


class TestCSVScenariosLoading:
    """Test suite for CSV scenarios loading via RecordDataSource."""

    def test_load_scenarios_csv(self, tmp_path: Path) -> None:
        """Test loading scenarios from CSV file."""
        scenarios_file = tmp_path / "scenarios.csv"
        with open(scenarios_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["scenario_id", "input", "expected"])
            writer.writerow(["scenario-1", "What is the capital of France?", "Paris"])
            writer.writerow(["scenario-2", "Explain quantum computing", ""])

        storage = LocalStorageBackend(tmp_path)
        source = RecordDataSource(storage, "scenarios.csv", schema=Scenario)
        scenarios = source.read()

        assert len(scenarios) == 2
        assert scenarios[0].scenario_id == "scenario-1"
        assert scenarios[0].input == "What is the capital of France?"
        assert scenarios[0].expected == "Paris"


class TestScenarioIteration:
    """Test suite for streaming scenarios."""

    def test_iter_scenarios(self, tmp_path: Path) -> None:
        """Test iterating over scenarios one at a time."""
        scenarios_file = tmp_path / "scenarios.jsonl"
        with open(scenarios_file, "w") as f:
            for i in range(5):
                f.write(f'{{"scenario_id": "s{i}", "input": "Test {i}"}}\n')

        storage = LocalStorageBackend(tmp_path)
        source = RecordDataSource(storage, "scenarios.jsonl", schema=Scenario)

        count = 0
        for scenario in source.iter():
            assert scenario.scenario_id == f"s{count}"
            count += 1

        assert count == 5


class TestPerformance:
    """Test suite for performance requirements."""

    def test_load_100_scenarios_performance(self, tmp_path: Path) -> None:
        """Test that 100 scenarios load in <100ms."""
        scenarios_data: List[Dict[str, Any]] = [
            {"scenario_id": f"scenario-{i}", "input": f"Test input {i}"} for i in range(100)
        ]

        scenarios_file = tmp_path / "scenarios.json"
        with open(scenarios_file, "w") as f:
            json.dump(scenarios_data, f)

        storage = LocalStorageBackend(tmp_path)
        source = RecordDataSource(storage, "scenarios.json", schema=Scenario)

        start = time.time()
        scenarios = source.read()
        elapsed = time.time() - start

        assert len(scenarios) == 100
        assert elapsed < 0.1  # <100ms

    def test_load_1000_scenarios_performance(self, tmp_path: Path) -> None:
        """Test that 1000 scenarios load in <1s."""
        scenarios_data: List[Dict[str, Any]] = [
            {"scenario_id": f"scenario-{i}", "input": f"Test input {i}"} for i in range(1000)
        ]

        scenarios_file = tmp_path / "scenarios.json"
        with open(scenarios_file, "w") as f:
            json.dump(scenarios_data, f)

        storage = LocalStorageBackend(tmp_path)
        source = RecordDataSource(storage, "scenarios.json", schema=Scenario)

        start = time.time()
        scenarios = source.read()
        elapsed = time.time() - start

        assert len(scenarios) == 1000
        assert elapsed < 1.0  # <1s
