"""
Unit tests for ResultsExporter.
"""

import hashlib
import json
from pathlib import Path

import jsonlines
import pytest

from gavel_ai.models.runtime import ProcessorResult, Scenario
from gavel_ai.storage.results_exporter import ResultsExporter


class TestResultsExporter:
    """Test ResultsExporter class."""

    def test_init(self, tmp_path: Path):
        """ResultsExporter initializes with run_dir and processor_type."""
        exporter = ResultsExporter(tmp_path, processor_type="prompt_input")

        assert exporter.run_dir == tmp_path
        assert exporter.processor_type == "prompt_input"

    def test_init_default_processor_type(self, tmp_path: Path):
        """ResultsExporter defaults to prompt_input processor type."""
        exporter = ResultsExporter(tmp_path)

        assert exporter.processor_type == "prompt_input"

    def test_export_raw_results_creates_file(self, tmp_path: Path):
        """export_raw_results creates results_raw.jsonl file."""
        exporter = ResultsExporter(tmp_path)

        scenarios = [Scenario(id="s1", input="test input", expected_output="expected")]
        processor_results = [ProcessorResult(output="output", metadata={})]

        result_file = exporter.export_raw_results(scenarios, processor_results)

        assert result_file == tmp_path / "results_raw.jsonl"
        assert result_file.exists()

    def test_export_raw_results_writes_correct_schema(self, tmp_path: Path):
        """export_raw_results writes entries with correct schema."""
        exporter = ResultsExporter(tmp_path)

        scenarios = [Scenario(id="s1", input="test", expected_output="expected")]
        processor_results = [
            ProcessorResult(
                output="test output",
                metadata={"latency_ms": 100, "tokens": {"prompt": 10, "completion": 20}},
            )
        ]

        exporter.export_raw_results(
            scenarios, processor_results, test_subject="assistant:v1", variant_id="claude-sonnet"
        )

        results_file = tmp_path / "results_raw.jsonl"
        with jsonlines.open(results_file) as reader:
            entries = list(reader)

        assert len(entries) == 1
        entry = entries[0]

        assert entry["test_subject"] == "assistant:v1"
        assert entry["variant_id"] == "claude-sonnet"
        assert entry["scenario_id"] == "s1"
        assert entry["processor_output"] == "test output"
        assert entry["timing_ms"] == 100
        assert entry["tokens_prompt"] == 10
        assert entry["tokens_completion"] == 20
        assert entry["error"] is None
        assert "timestamp" in entry

    def test_export_raw_results_handles_missing_metadata(self, tmp_path: Path):
        """export_raw_results handles empty metadata gracefully."""
        exporter = ResultsExporter(tmp_path)

        scenarios = [Scenario(id="s1", input="test", expected_output="expected")]
        processor_results = [ProcessorResult(output="output", metadata={})]

        exporter.export_raw_results(scenarios, processor_results)

        results_file = tmp_path / "results_raw.jsonl"
        with jsonlines.open(results_file) as reader:
            entries = list(reader)

        entry = entries[0]
        assert entry["timing_ms"] == 0
        assert entry["tokens_prompt"] == 0
        assert entry["tokens_completion"] == 0

    def test_export_raw_results_handles_error(self, tmp_path: Path):
        """export_raw_results includes error field for failed processors."""
        exporter = ResultsExporter(tmp_path)

        scenarios = [Scenario(id="s1", input="test", expected_output="expected")]
        processor_results = [ProcessorResult(output="", error="Timeout error", metadata={})]

        exporter.export_raw_results(scenarios, processor_results)

        results_file = tmp_path / "results_raw.jsonl"
        with jsonlines.open(results_file) as reader:
            entries = list(reader)

        assert entries[0]["error"] == "Timeout error"

    def test_export_raw_results_raises_on_length_mismatch(self, tmp_path: Path):
        """export_raw_results raises ValueError if counts don't match."""
        exporter = ResultsExporter(tmp_path)

        scenarios = [Scenario(id="s1", input="test", expected_output="expected")]
        processor_results = [
            ProcessorResult(output="out1", metadata={}),
            ProcessorResult(output="out2", metadata={}),
        ]

        with pytest.raises(ValueError, match="must match"):
            exporter.export_raw_results(scenarios, processor_results)

    def test_export_raw_results_handles_multiple_scenarios(self, tmp_path: Path):
        """export_raw_results handles multiple scenarios correctly."""
        exporter = ResultsExporter(tmp_path)

        scenarios = [
            Scenario(id="s1", input="test1", expected_output="expected1"),
            Scenario(id="s2", input="test2", expected_output="expected2"),
            Scenario(id="s3", input="test3", expected_output="expected3"),
        ]
        processor_results = [
            ProcessorResult(output="out1", metadata={}),
            ProcessorResult(output="out2", metadata={}),
            ProcessorResult(output="out3", metadata={}),
        ]

        exporter.export_raw_results(scenarios, processor_results)

        results_file = tmp_path / "results_raw.jsonl"
        with jsonlines.open(results_file) as reader:
            entries = list(reader)

        assert len(entries) == 3
        assert entries[0]["scenario_id"] == "s1"
        assert entries[1]["scenario_id"] == "s2"
        assert entries[2]["scenario_id"] == "s3"

    def test_export_judged_results_creates_file(self, tmp_path: Path):
        """export_judged_results creates results_judged.jsonl file."""
        exporter = ResultsExporter(tmp_path)

        scenarios = [Scenario(id="s1", input="test", expected_output="expected")]
        processor_results = [ProcessorResult(output="output", metadata={})]
        judge_evaluations = [{"judges": [{"name": "judge1", "score": 8}]}]

        result_file = exporter.export_judged_results(
            scenarios, processor_results, judge_evaluations
        )

        assert result_file == tmp_path / "results_judged.jsonl"
        assert result_file.exists()

    def test_export_judged_results_includes_judges_array(self, tmp_path: Path):
        """export_judged_results includes judges array in entries."""
        exporter = ResultsExporter(tmp_path)

        scenarios = [Scenario(id="s1", input="test", expected_output="expected")]
        processor_results = [ProcessorResult(output="output", metadata={})]
        judge_evaluations = [
            {
                "judges": [
                    {"name": "judge1", "score": 8, "reasoning": "Good response"},
                    {"name": "judge2", "score": 9, "reasoning": "Excellent"},
                ]
            }
        ]

        exporter.export_judged_results(scenarios, processor_results, judge_evaluations)

        results_file = tmp_path / "results_judged.jsonl"
        with jsonlines.open(results_file) as reader:
            entries = list(reader)

        assert len(entries) == 1
        assert "judges" in entries[0]
        assert len(entries[0]["judges"]) == 2
        assert entries[0]["judges"][0]["name"] == "judge1"
        assert entries[0]["judges"][1]["score"] == 9

    def test_export_judged_results_empty_judges_if_none(self, tmp_path: Path):
        """export_judged_results has empty judges array if no evaluations."""
        exporter = ResultsExporter(tmp_path)

        scenarios = [Scenario(id="s1", input="test", expected_output="expected")]
        processor_results = [ProcessorResult(output="output", metadata={})]

        exporter.export_judged_results(scenarios, processor_results, judge_evaluations=[])

        results_file = tmp_path / "results_judged.jsonl"
        with jsonlines.open(results_file) as reader:
            entries = list(reader)

        assert entries[0]["judges"] == []

    def test_export_judged_results_raises_on_scenario_mismatch(self, tmp_path: Path):
        """export_judged_results raises ValueError on scenario count mismatch."""
        exporter = ResultsExporter(tmp_path)

        scenarios = [Scenario(id="s1", input="test", expected_output="expected")]
        processor_results = [
            ProcessorResult(output="out1", metadata={}),
            ProcessorResult(output="out2", metadata={}),
        ]
        judge_evaluations = []

        with pytest.raises(ValueError, match="must match"):
            exporter.export_judged_results(scenarios, processor_results, judge_evaluations)

    def test_export_judged_results_raises_on_evaluation_mismatch(self, tmp_path: Path):
        """export_judged_results raises ValueError on evaluation count mismatch."""
        exporter = ResultsExporter(tmp_path)

        scenarios = [
            Scenario(id="s1", input="test1", expected_output="expected1"),
            Scenario(id="s2", input="test2", expected_output="expected2"),
        ]
        processor_results = [
            ProcessorResult(output="out1", metadata={}),
            ProcessorResult(output="out2", metadata={}),
        ]
        judge_evaluations = [{"judges": []}]  # Only 1 evaluation for 2 scenarios

        with pytest.raises(ValueError, match="must match"):
            exporter.export_judged_results(scenarios, processor_results, judge_evaluations)

    def test_export_judged_results_includes_processor_fields(self, tmp_path: Path):
        """export_judged_results includes all processor fields from raw schema."""
        exporter = ResultsExporter(tmp_path)

        scenarios = [Scenario(id="s1", input="test", expected_output="expected")]
        processor_results = [
            ProcessorResult(
                output="output",
                metadata={"latency_ms": 150, "tokens": {"prompt": 15, "completion": 25}},
            )
        ]
        judge_evaluations = [{"judges": [{"name": "judge1", "score": 8}]}]

        exporter.export_judged_results(
            scenarios, processor_results, judge_evaluations, test_subject="prompt:v2"
        )

        results_file = tmp_path / "results_judged.jsonl"
        with jsonlines.open(results_file) as reader:
            entries = list(reader)

        entry = entries[0]
        assert entry["test_subject"] == "prompt:v2"
        assert entry["scenario_id"] == "s1"
        assert entry["processor_output"] == "output"
        assert entry["timing_ms"] == 150
        assert entry["tokens_prompt"] == 15
        assert entry["tokens_completion"] == 25

    def test_compute_config_hash_returns_consistent_hash(self, tmp_path: Path):
        """compute_config_hash returns consistent SHA256 hash."""
        config1 = tmp_path / "config1.json"
        config1.write_text(json.dumps({"key": "value"}))

        hash1 = ResultsExporter.compute_config_hash({"config": config1})
        hash2 = ResultsExporter.compute_config_hash({"config": config1})

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_compute_config_hash_deterministic_ordering(self, tmp_path: Path):
        """compute_config_hash uses deterministic key ordering."""
        file1 = tmp_path / "file1.json"
        file1.write_text(json.dumps({"a": 1}))

        file2 = tmp_path / "file2.json"
        file2.write_text(json.dumps({"b": 2}))

        # Order shouldn't matter
        hash1 = ResultsExporter.compute_config_hash({"file1": file1, "file2": file2})
        hash2 = ResultsExporter.compute_config_hash({"file2": file2, "file1": file1})

        assert hash1 == hash2

    def test_compute_config_hash_different_for_different_content(self, tmp_path: Path):
        """compute_config_hash returns different hashes for different content."""
        file1 = tmp_path / "file1.json"
        file1.write_text(json.dumps({"key": "value1"}))

        file2 = tmp_path / "file2.json"
        file2.write_text(json.dumps({"key": "value2"}))

        hash1 = ResultsExporter.compute_config_hash({"config": file1})
        hash2 = ResultsExporter.compute_config_hash({"config": file2})

        assert hash1 != hash2

    def test_compute_config_hash_raises_file_not_found(self, tmp_path: Path):
        """compute_config_hash raises FileNotFoundError for missing files."""
        nonexistent = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            ResultsExporter.compute_config_hash({"config": nonexistent})

    def test_compute_config_hash_handles_multiple_files(self, tmp_path: Path):
        """compute_config_hash handles multiple config files."""
        file1 = tmp_path / "agents.json"
        file1.write_text(json.dumps({"agents": {}}))

        file2 = tmp_path / "eval_config.json"
        file2.write_text(json.dumps({"eval": {}}))

        file3 = tmp_path / "scenarios.json"
        file3.write_text(json.dumps({"scenarios": []}))

        hash_result = ResultsExporter.compute_config_hash(
            {
                "agents": file1,
                "eval_config": file2,
                "scenarios": file3,
            }
        )

        assert len(hash_result) == 64
        assert hash_result.isalnum()  # Valid hex string
