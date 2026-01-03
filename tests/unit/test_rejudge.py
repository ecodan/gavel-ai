"""
Unit tests for ReJudge.

Tests Story 4.7 acceptance criteria:
- Re-judge existing results without re-running evaluations
- New judges can be added
- Old judge results are preserved and new results are added
- Fast execution (no processor API calls)
"""

import tempfile
from pathlib import Path

import pytest

from gavel_ai.core.models import (
    EvaluationResult,
    JudgeConfig,
    JudgeEvaluation,
)
from gavel_ai.core.result_storage import ResultStorage
from gavel_ai.judges import ReJudge


@pytest.fixture
def temp_results_file():
    """Create a temporary results file with sample data."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False
    ) as f:
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def sample_stored_results():
    """Create sample stored results."""
    return [
        EvaluationResult(
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
                    reasoning="Highly relevant",
                    evidence="Correct answer",
                ),
            ],
            timestamp="2025-12-28T14:30:22Z",
            metadata={"run_id": "run-123"},
        ),
        EvaluationResult(
            scenario_id="scenario-2",
            variant_id="gpt-4",
            subject_id="put",
            scenario_input={"text": "What is the capital of Spain?"},
            expected_behavior="Madrid",
            processor_output="The capital of Spain is Madrid.",
            judges=[
                JudgeEvaluation(
                    judge_id="relevancy",
                    score=10,
                    reasoning="Perfect",
                    evidence="Accurate",
                ),
            ],
            timestamp="2025-12-28T14:30:23Z",
            metadata={"run_id": "run-123"},
        ),
    ]


class TestReJudgeBasics:
    """Test basic ReJudge functionality."""

    def test_rejudge_initialization(
        self, temp_results_file, mock_deepeval_metrics
    ):
        """Test initializing ReJudge engine."""
        configs = [
            JudgeConfig(
                name="faithfulness", type="deepeval.faithfulness"
            ),
        ]

        rejudge = ReJudge(temp_results_file, configs)

        assert rejudge.storage.results_file == temp_results_file
        assert len(rejudge.judge_executor.judges) == 1

    @pytest.mark.asyncio
    async def test_rejudge_all_empty_file(
        self, temp_results_file, mock_deepeval_metrics
    ):
        """Test re-judging with no existing results."""
        configs = [
            JudgeConfig(
                name="faithfulness", type="deepeval.faithfulness"
            ),
        ]

        rejudge = ReJudge(temp_results_file, configs)
        results = await rejudge.rejudge_all()

        assert results == []


class TestReJudgeAll:
    """Test re-judging all results."""

    @pytest.mark.asyncio
    async def test_rejudge_all_adds_new_judges(
        self,
        temp_results_file,
        sample_stored_results,
        mock_deepeval_metrics,
    ):
        """Test that re-judging adds new judge evaluations."""
        # Store initial results
        storage = ResultStorage(temp_results_file)
        storage.append_batch(sample_stored_results)

        # Setup mock for new judge
        mock_metric = mock_deepeval_metrics["faithfulness_instance"]
        mock_metric.score = 0.8
        mock_metric.reason = "Faithful"

        # Re-judge with new judge
        configs = [
            JudgeConfig(
                name="faithfulness", type="deepeval.faithfulness"
            ),
        ]
        rejudge = ReJudge(temp_results_file, configs)
        results = await rejudge.rejudge_all(preserve_existing=True)

        # Verify results
        assert len(results) == 2

        # Each result should have 2 judges now (relevancy + faithfulness)
        assert len(results[0].judges) == 2
        assert len(results[1].judges) == 2

        # Original judge should be preserved
        judge_ids = {j.judge_id for j in results[0].judges}
        assert "relevancy" in judge_ids
        assert "faithfulness" in judge_ids

    @pytest.mark.asyncio
    async def test_rejudge_all_updates_existing_judges(
        self,
        temp_results_file,
        sample_stored_results,
        mock_deepeval_metrics,
    ):
        """Test that re-judging updates existing judge evaluations."""
        # Store initial results
        storage = ResultStorage(temp_results_file)
        storage.append_batch(sample_stored_results)

        # Setup mock with different score
        mock_metric = mock_deepeval_metrics["relevancy_instance"]
        mock_metric.score = 0.5  # Different from stored score (9)
        mock_metric.reason = "Updated evaluation"

        # Re-judge with same judge (should update)
        configs = [
            JudgeConfig(
                name="relevancy", type="deepeval.answer_relevancy"
            ),
        ]
        rejudge = ReJudge(temp_results_file, configs)
        results = await rejudge.rejudge_all(preserve_existing=True)

        # Should have updated score
        assert results[0].judges[0].judge_id == "relevancy"
        assert results[0].judges[0].score == 6  # 0.5 -> 6 (updated)
        assert results[0].judges[0].reasoning == "Updated evaluation"

    @pytest.mark.asyncio
    async def test_rejudge_all_without_preserving(
        self,
        temp_results_file,
        sample_stored_results,
        mock_deepeval_metrics,
    ):
        """Test re-judging without preserving existing evaluations."""
        # Store initial results
        storage = ResultStorage(temp_results_file)
        storage.append_batch(sample_stored_results)

        # Setup mock for new judge
        mock_metric = mock_deepeval_metrics["faithfulness_instance"]
        mock_metric.score = 0.7
        mock_metric.reason = "New evaluation"

        # Re-judge with new judge, not preserving old
        configs = [
            JudgeConfig(
                name="faithfulness", type="deepeval.faithfulness"
            ),
        ]
        rejudge = ReJudge(temp_results_file, configs)
        results = await rejudge.rejudge_all(preserve_existing=False)

        # Should only have new judge
        assert len(results[0].judges) == 1
        assert results[0].judges[0].judge_id == "faithfulness"
        assert results[0].judges[0].score == 7  # 0.7 -> 7

    @pytest.mark.asyncio
    async def test_rejudge_all_writes_to_output_file(
        self,
        temp_results_file,
        sample_stored_results,
        mock_deepeval_metrics,
    ):
        """Test that re-judged results are written to file."""
        # Store initial results
        storage = ResultStorage(temp_results_file)
        storage.append_batch(sample_stored_results)

        # Setup mock
        mock_metric = mock_deepeval_metrics["faithfulness_instance"]
        mock_metric.score = 0.8
        mock_metric.reason = "Good"

        # Re-judge
        configs = [
            JudgeConfig(
                name="faithfulness", type="deepeval.faithfulness"
            ),
        ]
        rejudge = ReJudge(temp_results_file, configs)
        await rejudge.rejudge_all(preserve_existing=True)

        # Load from file and verify
        loaded_results = storage.load_all()
        assert len(loaded_results) == 2
        assert len(loaded_results[0].judges) == 2  # Original + new
        assert len(loaded_results[1].judges) == 2  # Original + new


class TestReJudgeFiltering:
    """Test re-judging with filtering."""

    @pytest.mark.asyncio
    async def test_rejudge_by_scenario(
        self,
        temp_results_file,
        sample_stored_results,
        mock_deepeval_metrics,
    ):
        """Test re-judging filtered by scenario."""
        # Store initial results
        storage = ResultStorage(temp_results_file)
        storage.append_batch(sample_stored_results)

        # Setup mock
        mock_metric = mock_deepeval_metrics["faithfulness_instance"]
        mock_metric.score = 0.9
        mock_metric.reason = "Excellent"

        # Re-judge only scenario-1
        configs = [
            JudgeConfig(
                name="faithfulness", type="deepeval.faithfulness"
            ),
        ]
        rejudge = ReJudge(temp_results_file, configs)
        results = await rejudge.rejudge_by_scenario("scenario-1")

        # Should only have 1 result (scenario-1)
        assert len(results) == 1
        assert results[0].scenario_id == "scenario-1"
        assert len(results[0].judges) == 2  # Original + new

    @pytest.mark.asyncio
    async def test_rejudge_by_variant(
        self,
        temp_results_file,
        sample_stored_results,
        mock_deepeval_metrics,
    ):
        """Test re-judging filtered by variant."""
        # Store initial results
        storage = ResultStorage(temp_results_file)
        storage.append_batch(sample_stored_results)

        # Setup mock
        mock_metric = mock_deepeval_metrics["faithfulness_instance"]
        mock_metric.score = 0.85
        mock_metric.reason = "Very good"

        # Re-judge only claude-sonnet variant
        configs = [
            JudgeConfig(
                name="faithfulness", type="deepeval.faithfulness"
            ),
        ]
        rejudge = ReJudge(temp_results_file, configs)
        results = await rejudge.rejudge_by_variant("claude-sonnet")

        # Should only have 1 result (claude-sonnet)
        assert len(results) == 1
        assert results[0].variant_id == "claude-sonnet"
        assert len(results[0].judges) == 2  # Original + new

    @pytest.mark.asyncio
    async def test_rejudge_nonexistent_scenario(
        self,
        temp_results_file,
        sample_stored_results,
        mock_deepeval_metrics,
    ):
        """Test re-judging with non-existent scenario."""
        # Store initial results
        storage = ResultStorage(temp_results_file)
        storage.append_batch(sample_stored_results)

        # Re-judge non-existent scenario
        configs = [
            JudgeConfig(
                name="faithfulness", type="deepeval.faithfulness"
            ),
        ]
        rejudge = ReJudge(temp_results_file, configs)
        results = await rejudge.rejudge_by_scenario("nonexistent")

        assert results == []


class TestReJudgeMultipleJudges:
    """Test re-judging with multiple judges."""

    @pytest.mark.asyncio
    async def test_rejudge_with_multiple_new_judges(
        self,
        temp_results_file,
        sample_stored_results,
        mock_deepeval_metrics,
    ):
        """Test re-judging with multiple new judges."""
        # Store initial results
        storage = ResultStorage(temp_results_file)
        storage.append_batch(sample_stored_results)

        # Setup mocks
        mock_faithfulness = mock_deepeval_metrics["faithfulness_instance"]
        mock_faithfulness.score = 0.8
        mock_faithfulness.reason = "Faithful"

        mock_geval = mock_deepeval_metrics["geval_instance"]
        mock_geval.score = 0.75
        mock_geval.reason = "Good quality"

        # Re-judge with two new judges
        configs = [
            JudgeConfig(
                name="faithfulness", type="deepeval.faithfulness"
            ),
            JudgeConfig(
                name="quality",
                type="deepeval.geval",
                config={
                    "name": "quality",
                    "criteria": "Quality",
                    "evaluation_steps": ["Check quality"],
                },
            ),
        ]
        rejudge = ReJudge(temp_results_file, configs)
        results = await rejudge.rejudge_all(preserve_existing=True)

        # Each result should have 3 judges (relevancy + faithfulness + quality)
        assert len(results[0].judges) == 3

        judge_ids = {j.judge_id for j in results[0].judges}
        assert "relevancy" in judge_ids
        assert "faithfulness" in judge_ids
        assert "quality" in judge_ids
