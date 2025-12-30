"""
Unit tests for DeepEval judge integration.

Tests Story 4.2 acceptance criteria:
- DeepEval judges can be instantiated
- Evaluation logic executes correctly
- Results are wrapped in JudgeResult with scores normalized to 1-10
- Errors are wrapped in JudgeError with recovery guidance
"""

from unittest.mock import MagicMock

import pytest

from gavel_ai.core.exceptions import JudgeError
from gavel_ai.core.models import JudgeConfig, JudgeResult, Scenario
from gavel_ai.judges.deepeval_judge import DeepEvalJudge


@pytest.fixture
def answer_relevancy_config():
    """Create config for answer relevancy judge."""
    return JudgeConfig(
        judge_id="relevancy",
        judge_type="deepeval.answer_relevancy",
        threshold=0.7,
        config={"model": "gpt-4"},
    )


@pytest.fixture
def faithfulness_config():
    """Create config for faithfulness judge."""
    return JudgeConfig(
        judge_id="faithfulness",
        judge_type="deepeval.faithfulness",
        threshold=0.8,
    )


@pytest.fixture
def geval_config():
    """Create config for GEval judge."""
    return JudgeConfig(
        judge_id="custom",
        judge_type="deepeval.geval",
        threshold=0.7,
        config={
            "name": "custom_quality",
            "criteria": "Evaluate response quality",
            "evaluation_steps": ["Check accuracy", "Evaluate clarity"],
            "model": "gpt-4",
        },
    )


@pytest.fixture
def mock_scenario():
    """Create a test scenario."""
    return Scenario(
        id="scenario-1",
        input={
            "text": "What is the capital of France?",
            "context": "Geography question",
        },
        expected_behavior="Paris",
    )


class TestDeepEvalJudgeInitialization:
    """Test DeepEvalJudge initialization."""

    def test_answer_relevancy_judge_creation(
        self, mock_deepeval_metrics, answer_relevancy_config
    ):
        """Test creating answer relevancy judge."""
        judge = DeepEvalJudge(answer_relevancy_config)

        assert judge.config == answer_relevancy_config
        assert judge.metric == mock_deepeval_metrics["relevancy_instance"]
        mock_deepeval_metrics["AnswerRelevancyMetric"].assert_called_once_with(
            threshold=0.7, model="gpt-4"
        )

    def test_faithfulness_judge_creation(
        self, mock_deepeval_metrics, faithfulness_config
    ):
        """Test creating faithfulness judge."""
        judge = DeepEvalJudge(faithfulness_config)

        assert judge.config == faithfulness_config
        assert judge.metric == mock_deepeval_metrics["faithfulness_instance"]
        mock_deepeval_metrics["FaithfulnessMetric"].assert_called_once_with(
            threshold=0.8
        )

    def test_geval_judge_creation(self, mock_deepeval_metrics, geval_config):
        """Test creating GEval judge."""
        judge = DeepEvalJudge(geval_config)

        assert judge.config == geval_config
        assert judge.metric == mock_deepeval_metrics["geval_instance"]
        mock_deepeval_metrics["GEval"].assert_called_once_with(
            name="custom_quality",
            criteria="Evaluate response quality",
            evaluation_steps=["Check accuracy", "Evaluate clarity"],
            model="gpt-4",
            threshold=0.7,
        )

    def test_unsupported_judge_type_raises_error(self, mock_deepeval_metrics):
        """Test that unsupported judge type raises JudgeError."""
        config = JudgeConfig(
            judge_id="unsupported",
            judge_type="deepeval.unknown",
        )

        with pytest.raises(JudgeError) as exc_info:
            DeepEvalJudge(config)

        assert "Unsupported DeepEval judge type" in str(exc_info.value)
        assert "deepeval.unknown" in str(exc_info.value)


class TestDeepEvalJudgeEvaluation:
    """Test DeepEvalJudge evaluation."""

    @pytest.mark.asyncio
    async def test_evaluate_with_high_score(
        self, mock_deepeval_metrics, answer_relevancy_config, mock_scenario
    ):
        """Test evaluation with high score."""
        # Setup mock metric behavior
        mock_metric = mock_deepeval_metrics["relevancy_instance"]
        mock_metric.score = 0.95  # High score
        mock_metric.reason = "Highly relevant and accurate"

        judge = DeepEvalJudge(answer_relevancy_config)
        result = await judge.evaluate(mock_scenario, "The capital is Paris")

        # Verify result
        assert isinstance(result, JudgeResult)
        assert result.score == 10  # 0.95 -> 10
        assert "Highly relevant" in result.reasoning
        assert "0.950" in result.evidence

        # Verify metric was called
        mock_metric.measure.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_with_medium_score(
        self, mock_deepeval_metrics, faithfulness_config, mock_scenario
    ):
        """Test evaluation with medium score."""
        # Setup mock metric behavior
        mock_metric = mock_deepeval_metrics["faithfulness_instance"]
        mock_metric.score = 0.55  # Medium score
        mock_metric.reason = "Partially faithful"

        judge = DeepEvalJudge(faithfulness_config)
        result = await judge.evaluate(mock_scenario, "Paris is nice")

        # Verify result
        assert isinstance(result, JudgeResult)
        assert result.score == 6  # 0.55 -> 6
        assert "Partially faithful" in result.reasoning

    @pytest.mark.asyncio
    async def test_evaluate_with_low_score(
        self, mock_deepeval_metrics, answer_relevancy_config, mock_scenario
    ):
        """Test evaluation with low score."""
        # Setup mock metric behavior
        mock_metric = mock_deepeval_metrics["relevancy_instance"]
        mock_metric.score = 0.1  # Low score
        mock_metric.reason = "Not relevant"

        judge = DeepEvalJudge(answer_relevancy_config)
        result = await judge.evaluate(mock_scenario, "I don't know")

        # Verify result
        assert isinstance(result, JudgeResult)
        assert result.score == 2  # 0.1 -> 2
        assert "Not relevant" in result.reasoning

    @pytest.mark.asyncio
    async def test_evaluate_with_geval(
        self, mock_deepeval_metrics, geval_config, mock_scenario
    ):
        """Test evaluation with custom GEval judge."""
        # Setup mock metric behavior
        mock_metric = mock_deepeval_metrics["geval_instance"]
        mock_metric.score = 0.85  # High score for custom criteria
        mock_metric.reason = "Meets custom quality criteria: accurate and clear"

        judge = DeepEvalJudge(geval_config)
        result = await judge.evaluate(mock_scenario, "Paris is the capital")

        # Verify result
        assert isinstance(result, JudgeResult)
        assert result.score == 9  # 0.85 -> 9
        assert "custom quality criteria" in result.reasoning
        assert "0.850" in result.evidence

        # Verify metric was called correctly
        mock_metric.measure.assert_called_once()


class TestDeepEvalJudgeErrorHandling:
    """Test DeepEvalJudge error handling."""

    @pytest.mark.asyncio
    async def test_evaluation_failure_raises_judge_error(
        self, mock_deepeval_metrics, answer_relevancy_config, mock_scenario
    ):
        """Test that evaluation failures raise JudgeError."""
        # Setup mock metric to raise exception
        mock_metric = mock_deepeval_metrics["relevancy_instance"]
        mock_metric.measure.side_effect = Exception("API error")

        judge = DeepEvalJudge(answer_relevancy_config)

        with pytest.raises(JudgeError) as exc_info:
            await judge.evaluate(mock_scenario, "test output")

        assert "DeepEval evaluation failed" in str(exc_info.value)
        assert "API error" in str(exc_info.value)
        assert "Check API credentials" in str(exc_info.value)


class TestDeepEvalJudgeScoreNormalization:
    """Test score normalization."""

    def test_score_normalization_boundary_values(
        self, mock_deepeval_metrics, answer_relevancy_config
    ):
        """Test score normalization at boundaries."""
        judge = DeepEvalJudge(answer_relevancy_config)

        # Test boundary values
        assert judge._normalize_score(0.0) == 1
        assert judge._normalize_score(1.0) == 10
        assert judge._normalize_score(0.5) == 6

    def test_score_normalization_range(
        self, mock_deepeval_metrics, answer_relevancy_config
    ):
        """Test score normalization across range."""
        judge = DeepEvalJudge(answer_relevancy_config)

        # Test various scores
        # Formula: round(1 + raw_score * 9)
        test_cases = [
            (0.0, 1),   # round(1 + 0*9) = 1
            (0.1, 2),   # round(1 + 0.9) = 2
            (0.2, 3),   # round(1 + 1.8) = 3
            (0.3, 4),   # round(1 + 2.7) = 4
            (0.4, 5),   # round(1 + 3.6) = 5
            (0.5, 6),   # round(1 + 4.5) = 6
            (0.6, 6),   # round(1 + 5.4) = 6
            (0.7, 7),   # round(1 + 6.3) = 7
            (0.8, 8),   # round(1 + 7.2) = 8
            (0.9, 9),   # round(1 + 8.1) = 9
            (1.0, 10),  # round(1 + 9.0) = 10
        ]

        for raw_score, expected_normalized in test_cases:
            normalized = judge._normalize_score(raw_score)
            assert normalized == expected_normalized
            assert 1 <= normalized <= 10
