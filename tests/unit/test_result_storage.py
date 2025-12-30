"""
Unit tests for ResultStorage.

Tests Story 4.6 acceptance criteria:
- Results written to results.jsonl (one JSON object per line)
- Results can be loaded for re-judging
- JSONL format with all required fields
"""

import json
import tempfile
from pathlib import Path

import pytest

from gavel_ai.core.models import EvaluationResult, JudgeEvaluation
from gavel_ai.core.result_storage import ResultStorage


@pytest.fixture
def temp_results_file():
    """Create a temporary results file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False
    ) as f:
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def sample_result():
    """Create a sample evaluation result."""
    return EvaluationResult(
        scenario_id="scenario-1",
        variant_id="claude-sonnet",
        subject_id="put",
        scenario_input={"text": "What is the capital of France?"},
        expected_behavior="Paris",
        processor_output="The capital of France is Paris.",
        judges=[
            JudgeEvaluation(
                judge_id="relevancy",
                score=9,
                reasoning="Highly relevant and accurate",
                evidence="Correct answer",
            ),
            JudgeEvaluation(
                judge_id="faithfulness",
                score=10,
                reasoning="Completely faithful",
                evidence="No hallucinations",
            ),
        ],
        timestamp="2025-12-28T14:30:22Z",
        metadata={"run_id": "run-123"},
    )


class TestResultStorageBasics:
    """Test basic ResultStorage functionality."""

    def test_create_storage_creates_parent_dirs(self):
        """Test that creating storage creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            results_file = Path(tmpdir) / "runs" / "run-123" / "results.jsonl"
            storage = ResultStorage(results_file)

            assert storage.results_file.parent.exists()

    def test_append_result(self, temp_results_file, sample_result):
        """Test appending a single result."""
        storage = ResultStorage(temp_results_file)
        storage.append(sample_result)

        # Verify file exists and contains data
        assert temp_results_file.exists()

        # Load and verify
        with open(temp_results_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 1

        # Parse JSON
        data = json.loads(lines[0])
        assert data["scenario_id"] == "scenario-1"
        assert data["variant_id"] == "claude-sonnet"
        assert len(data["judges"]) == 2

    def test_append_multiple_results(self, temp_results_file, sample_result):
        """Test appending multiple results sequentially."""
        storage = ResultStorage(temp_results_file)

        # Append multiple results
        result1 = sample_result
        result2 = sample_result.model_copy(
            update={"scenario_id": "scenario-2", "variant_id": "gpt-4"}
        )
        result3 = sample_result.model_copy(update={"scenario_id": "scenario-3"})

        storage.append(result1)
        storage.append(result2)
        storage.append(result3)

        # Verify file has 3 lines
        with open(temp_results_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 3

    def test_append_batch(self, temp_results_file, sample_result):
        """Test appending batch of results."""
        storage = ResultStorage(temp_results_file)

        results = [
            sample_result,
            sample_result.model_copy(update={"scenario_id": "scenario-2"}),
            sample_result.model_copy(update={"scenario_id": "scenario-3"}),
        ]

        storage.append_batch(results)

        # Verify file has 3 lines
        with open(temp_results_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 3


class TestResultStorageLoading:
    """Test loading results from storage."""

    def test_load_all_empty_file(self, temp_results_file):
        """Test loading from non-existent file returns empty list."""
        storage = ResultStorage(temp_results_file)
        results = storage.load_all()

        assert results == []

    def test_load_all_results(self, temp_results_file, sample_result):
        """Test loading all results."""
        storage = ResultStorage(temp_results_file)

        # Store results
        results_to_store = [
            sample_result,
            sample_result.model_copy(update={"scenario_id": "scenario-2"}),
            sample_result.model_copy(update={"scenario_id": "scenario-3"}),
        ]
        storage.append_batch(results_to_store)

        # Load results
        loaded_results = storage.load_all()

        assert len(loaded_results) == 3
        assert loaded_results[0].scenario_id == "scenario-1"
        assert loaded_results[1].scenario_id == "scenario-2"
        assert loaded_results[2].scenario_id == "scenario-3"

    def test_load_preserves_judge_evaluations(
        self, temp_results_file, sample_result
    ):
        """Test that loading preserves judge evaluations."""
        storage = ResultStorage(temp_results_file)
        storage.append(sample_result)

        loaded_results = storage.load_all()
        assert len(loaded_results) == 1

        result = loaded_results[0]
        assert len(result.judges) == 2
        assert result.judges[0].judge_id == "relevancy"
        assert result.judges[0].score == 9
        assert result.judges[1].judge_id == "faithfulness"
        assert result.judges[1].score == 10

    def test_load_preserves_metadata(self, temp_results_file, sample_result):
        """Test that loading preserves metadata."""
        storage = ResultStorage(temp_results_file)
        storage.append(sample_result)

        loaded_results = storage.load_all()
        assert loaded_results[0].metadata == {"run_id": "run-123"}

    def test_iterate_results(self, temp_results_file, sample_result):
        """Test iterating over results without loading all into memory."""
        storage = ResultStorage(temp_results_file)

        # Store multiple results
        for i in range(5):
            result = sample_result.model_copy(
                update={"scenario_id": f"scenario-{i}"}
            )
            storage.append(result)

        # Iterate and collect
        iterated_results = list(storage.iterate())

        assert len(iterated_results) == 5
        assert iterated_results[0].scenario_id == "scenario-0"
        assert iterated_results[4].scenario_id == "scenario-4"

    def test_iterate_empty_file(self, temp_results_file):
        """Test iterating over non-existent file."""
        storage = ResultStorage(temp_results_file)
        iterated_results = list(storage.iterate())

        assert iterated_results == []


class TestResultStorageFiltering:
    """Test filtering results."""

    def test_filter_by_scenario(self, temp_results_file, sample_result):
        """Test filtering results by scenario ID."""
        storage = ResultStorage(temp_results_file)

        # Store results for different scenarios
        storage.append_batch(
            [
                sample_result.model_copy(update={"scenario_id": "s1"}),
                sample_result.model_copy(update={"scenario_id": "s2"}),
                sample_result.model_copy(update={"scenario_id": "s1"}),
                sample_result.model_copy(update={"scenario_id": "s3"}),
            ]
        )

        # Filter by scenario
        s1_results = storage.filter_by_scenario("s1")

        assert len(s1_results) == 2
        assert all(r.scenario_id == "s1" for r in s1_results)

    def test_filter_by_variant(self, temp_results_file, sample_result):
        """Test filtering results by variant ID."""
        storage = ResultStorage(temp_results_file)

        # Store results for different variants
        storage.append_batch(
            [
                sample_result.model_copy(update={"variant_id": "claude-sonnet"}),
                sample_result.model_copy(update={"variant_id": "gpt-4"}),
                sample_result.model_copy(update={"variant_id": "claude-sonnet"}),
                sample_result.model_copy(update={"variant_id": "gpt-4"}),
            ]
        )

        # Filter by variant
        claude_results = storage.filter_by_variant("claude-sonnet")

        assert len(claude_results) == 2
        assert all(r.variant_id == "claude-sonnet" for r in claude_results)


class TestResultStorageClear:
    """Test clearing storage."""

    def test_clear_removes_file(self, temp_results_file, sample_result):
        """Test that clear removes the results file."""
        storage = ResultStorage(temp_results_file)
        storage.append(sample_result)

        assert temp_results_file.exists()

        storage.clear()

        assert not temp_results_file.exists()

    def test_clear_nonexistent_file(self, temp_results_file):
        """Test clearing non-existent file doesn't raise error."""
        storage = ResultStorage(temp_results_file)

        # Should not raise
        storage.clear()


class TestResultStorageJSONLFormat:
    """Test JSONL format compliance."""

    def test_each_result_on_own_line(self, temp_results_file, sample_result):
        """Test that each result is on its own line."""
        storage = ResultStorage(temp_results_file)

        storage.append_batch(
            [
                sample_result,
                sample_result.model_copy(update={"scenario_id": "scenario-2"}),
                sample_result.model_copy(update={"scenario_id": "scenario-3"}),
            ]
        )

        with open(temp_results_file, "r") as f:
            lines = f.readlines()

        # Each line should be valid JSON
        assert len(lines) == 3
        for line in lines:
            data = json.loads(line.strip())
            assert "scenario_id" in data
            assert "variant_id" in data
            assert "judges" in data

    def test_jsonl_contains_all_required_fields(
        self, temp_results_file, sample_result
    ):
        """Test that JSONL contains all required fields per spec."""
        storage = ResultStorage(temp_results_file)
        storage.append(sample_result)

        with open(temp_results_file, "r") as f:
            data = json.loads(f.readline())

        # Verify required fields per Epic 4 Story 4.6
        required_fields = [
            "scenario_id",
            "variant_id",
            "subject_id",
            "scenario_input",
            "expected_behavior",
            "processor_output",
            "judges",
            "timestamp",
        ]

        for field in required_fields:
            assert field in data

        # Verify judges array structure
        assert isinstance(data["judges"], list)
        assert len(data["judges"]) == 2

        judge = data["judges"][0]
        assert "judge_id" in judge
        assert "score" in judge
        assert "reasoning" in judge
        assert "evidence" in judge
