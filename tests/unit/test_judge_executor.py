"""
Unit tests for JudgeExecutor.

Tests Story 4.5 acceptance criteria:
- Judges execute sequentially (Judge A evaluates all outputs, then Judge B, etc.)
- All judge results are preserved in evaluation result
- Error handling works correctly (fail_fast vs continue_on_error)
"""

import pytest

from gavel_ai.core.exceptions import JudgeError
from gavel_ai.core.models import EvaluationResult, JudgeConfig, Scenario
from gavel_ai.judges import JudgeExecutor


class TestJudgeExecutorInitialization:
    """Test JudgeExecutor initialization."""

    def test_create_executor_with_judges(self, mock_deepeval_metrics):
        """Test creating executor with valid judge configs."""
        configs = [
            JudgeConfig(name="relevancy", type="deepeval.answer_relevancy"),
            JudgeConfig(name="faithfulness", type="deepeval.faithfulness"),
        ]

        executor = JudgeExecutor(configs)

        assert len(executor.judges) == 2
        assert executor.error_handling == "fail_fast"

    def test_create_executor_with_custom_error_handling(self, mock_deepeval_metrics):
        """Test creating executor with custom error handling."""
        configs = [
            JudgeConfig(name="test", type="deepeval.answer_relevancy"),
        ]

        executor = JudgeExecutor(configs, error_handling="continue_on_error")

        assert executor.error_handling == "continue_on_error"

    def test_create_executor_with_no_judges_raises_error(self):
        """Test that creating executor with empty configs raises error."""
        with pytest.raises(JudgeError) as exc_info:
            JudgeExecutor([])

        assert "at least one judge" in str(exc_info.value)

    def test_create_executor_with_invalid_judge_raises_error(self, mock_deepeval_metrics):
        """Test that invalid judge config raises error during initialization."""
        configs = [
            JudgeConfig(name="invalid", type="invalid.type"),
        ]

        with pytest.raises(JudgeError) as exc_info:
            JudgeExecutor(configs)

        assert "Failed to create judge" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)


class TestJudgeExecutorSingleExecution:
    """Test single execution with JudgeExecutor."""

    @pytest.mark.asyncio
    async def test_execute_single_judge(self, mock_deepeval_metrics):
        """Test executing a single judge."""
        # Setup mock
        mock_metric = mock_deepeval_metrics["relevancy_instance"]
        mock_metric.score = 0.9
        mock_metric.reason = "Highly relevant"

        # Create executor
        config = JudgeConfig(name="relevancy", type="deepeval.answer_relevancy")
        executor = JudgeExecutor([config])

        # Execute
        scenario = Scenario(
            id="test-scenario",
            input={"text": "What is the capital of France?"},
            expected_behavior="Paris",
        )
        result = await executor.execute(
            scenario=scenario,
            subject_output="The capital is Paris",
            variant_id="claude-sonnet",
        )

        # Verify result
        assert isinstance(result, EvaluationResult)
        assert result.scenario_id == "test-scenario"
        assert result.variant_id == "claude-sonnet"
        assert result.subject_id == "put"
        assert result.processor_output == "The capital is Paris"
        assert len(result.judges) == 1
        assert result.judges[0].judge_id == "relevancy"
        assert result.judges[0].score == 9  # 0.9 -> 9
        assert result.judges[0].reasoning == "Highly relevant"
        assert result.timestamp  # Should have timestamp

    @pytest.mark.asyncio
    async def test_execute_multiple_judges_sequentially(self, mock_deepeval_metrics):
        """Test executing multiple judges sequentially."""
        # Setup mocks
        mock_relevancy = mock_deepeval_metrics["relevancy_instance"]
        mock_relevancy.score = 0.85
        mock_relevancy.reason = "Relevant"

        mock_faithfulness = mock_deepeval_metrics["faithfulness_instance"]
        mock_faithfulness.score = 0.75
        mock_faithfulness.reason = "Mostly faithful"

        # Create executor with two judges
        configs = [
            JudgeConfig(name="relevancy", type="deepeval.answer_relevancy"),
            JudgeConfig(name="faithfulness", type="deepeval.faithfulness"),
        ]
        executor = JudgeExecutor(configs)

        # Execute
        scenario = Scenario(
            id="test-scenario",
            input={"text": "Test question"},
        )
        result = await executor.execute(
            scenario=scenario,
            subject_output="Test answer",
            variant_id="gpt-4",
        )

        # Verify both judges executed
        assert len(result.judges) == 2

        # First judge (relevancy)
        assert result.judges[0].judge_id == "relevancy"
        assert result.judges[0].score == 9  # 0.85 -> 9

        # Second judge (faithfulness)
        assert result.judges[1].judge_id == "faithfulness"
        assert result.judges[1].score == 8  # 0.75 -> 8

    @pytest.mark.asyncio
    async def test_execute_with_custom_subject_id(self, mock_deepeval_metrics):
        """Test execution with custom subject_id."""
        mock_metric = mock_deepeval_metrics["relevancy_instance"]
        mock_metric.score = 0.5
        mock_metric.reason = "Okay"

        config = JudgeConfig(name="test", type="deepeval.answer_relevancy")
        executor = JudgeExecutor([config])

        scenario = Scenario(id="test", input={"text": "test"})
        result = await executor.execute(
            scenario=scenario,
            subject_output="answer",
            variant_id="model-1",
            subject_id="sut",  # Custom subject_id
        )

        assert result.subject_id == "sut"

    @pytest.mark.asyncio
    async def test_execute_with_metadata(self, mock_deepeval_metrics):
        """Test execution with custom metadata."""
        mock_metric = mock_deepeval_metrics["relevancy_instance"]
        mock_metric.score = 0.5
        mock_metric.reason = "Okay"

        config = JudgeConfig(name="test", type="deepeval.answer_relevancy")
        executor = JudgeExecutor([config])

        scenario = Scenario(id="test", input={"text": "test"})
        metadata = {"run_id": "run-123", "environment": "test"}

        result = await executor.execute(
            scenario=scenario,
            subject_output="answer",
            variant_id="model-1",
            metadata=metadata,
        )

        assert result.metadata == metadata


class TestJudgeExecutorErrorHandling:
    """Test error handling in JudgeExecutor."""

    @pytest.mark.asyncio
    async def test_fail_fast_stops_on_first_error(self, mock_deepeval_metrics):
        """Test that fail_fast stops execution on first error."""
        # Setup: first judge succeeds, second judge fails
        mock_relevancy = mock_deepeval_metrics["relevancy_instance"]
        mock_relevancy.score = 0.9
        mock_relevancy.reason = "Good"

        mock_faithfulness = mock_deepeval_metrics["faithfulness_instance"]
        mock_faithfulness.measure.side_effect = Exception("API error")

        configs = [
            JudgeConfig(name="relevancy", type="deepeval.answer_relevancy"),
            JudgeConfig(name="faithfulness", type="deepeval.faithfulness"),
        ]
        executor = JudgeExecutor(configs, error_handling="fail_fast")

        scenario = Scenario(id="test", input={"text": "test"})

        with pytest.raises(JudgeError) as exc_info:
            await executor.execute(
                scenario=scenario,
                subject_output="answer",
                variant_id="model-1",
            )

        assert "faithfulness" in str(exc_info.value)
        assert "failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_continue_on_error_skips_failed_judge(self, mock_deepeval_metrics):
        """Test that continue_on_error skips failed judge and continues."""
        # Setup: first judge fails, second judge succeeds
        mock_relevancy = mock_deepeval_metrics["relevancy_instance"]
        mock_relevancy.measure.side_effect = Exception("API error")

        mock_faithfulness = mock_deepeval_metrics["faithfulness_instance"]
        mock_faithfulness.score = 0.8
        mock_faithfulness.reason = "Good"

        configs = [
            JudgeConfig(name="relevancy", type="deepeval.answer_relevancy"),
            JudgeConfig(name="faithfulness", type="deepeval.faithfulness"),
        ]
        executor = JudgeExecutor(configs, error_handling="continue_on_error")

        scenario = Scenario(id="test", input={"text": "test"})
        result = await executor.execute(
            scenario=scenario,
            subject_output="answer",
            variant_id="model-1",
        )

        # Should have only the second judge's result
        assert len(result.judges) == 1
        assert result.judges[0].judge_id == "faithfulness"
        assert result.judges[0].score == 8


class TestJudgeExecutorBatchExecution:
    """Test batch execution with JudgeExecutor."""

    @pytest.mark.asyncio
    async def test_execute_batch(self, mock_deepeval_metrics):
        """Test executing batch of evaluations."""
        # Setup mock
        mock_metric = mock_deepeval_metrics["relevancy_instance"]
        mock_metric.score = 0.9
        mock_metric.reason = "Good"

        config = JudgeConfig(name="test", type="deepeval.answer_relevancy")
        executor = JudgeExecutor([config])

        # Create batch of evaluations
        evaluations = [
            (
                Scenario(id="s1", input={"text": "q1"}),
                "answer1",
                "model-1",
            ),
            (
                Scenario(id="s2", input={"text": "q2"}),
                "answer2",
                "model-2",
            ),
            (
                Scenario(id="s3", input={"text": "q3"}),
                "answer3",
                "model-1",
            ),
        ]

        results = await executor.execute_batch(evaluations)

        # Verify results
        assert len(results) == 3
        assert results[0].scenario_id == "s1"
        assert results[0].variant_id == "model-1"
        assert results[1].scenario_id == "s2"
        assert results[1].variant_id == "model-2"
        assert results[2].scenario_id == "s3"
        assert results[2].variant_id == "model-1"

    @pytest.mark.asyncio
    async def test_execute_batch_with_metadata(self, mock_deepeval_metrics):
        """Test batch execution with shared metadata."""
        mock_metric = mock_deepeval_metrics["relevancy_instance"]
        mock_metric.score = 0.5
        mock_metric.reason = "Okay"

        config = JudgeConfig(name="test", type="deepeval.answer_relevancy")
        executor = JudgeExecutor([config])

        evaluations = [
            (Scenario(id="s1", input={"text": "q1"}), "a1", "m1"),
        ]
        metadata = {"batch_id": "batch-123"}

        results = await executor.execute_batch(evaluations, metadata=metadata)

        assert results[0].metadata == metadata
