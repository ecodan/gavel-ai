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
from deepeval.test_case import LLMTestCaseParams

from gavel_ai.core.exceptions import JudgeError
from gavel_ai.core.models import JudgeConfig, JudgeResult, Scenario
from gavel_ai.judges.deepeval_judge import DeepEvalJudge


@pytest.fixture
def answer_relevancy_config():
    """Create config for answer relevancy judge."""
    return JudgeConfig(
        name="relevancy",
        type="deepeval.answer_relevancy",
        threshold=0.7,
        config={"model": "gpt-4"},
    )


@pytest.fixture
def faithfulness_config():
    """Create config for faithfulness judge."""
    return JudgeConfig(
        name="faithfulness",
        type="deepeval.faithfulness",
        threshold=0.8,
    )


@pytest.fixture
def geval_config():
    """Create config for GEval judge."""
    return JudgeConfig(
        name="custom",
        type="deepeval.geval",
        threshold=0.7,
        config={
            "name": "custom_quality",
            "criteria": "Evaluate response quality",
            "evaluation_steps": ["Check accuracy", "Evaluate clarity"],
            "model": "gpt-4",
        },
    )


@pytest.fixture
def geval_config_with_template():
    """Create config for GEval judge with expected_output_template."""
    return JudgeConfig(
        name="custom_template",
        type="deepeval.geval",
        threshold=0.7,
        config={
            "name": "template_quality",
            "criteria": "Evaluate response quality",
            "evaluation_steps": ["Check accuracy", "Evaluate clarity"],
            "expected_output_template": "The capital of {{country}} is {{capital}}",
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
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
            ],
            model="gpt-4",
            threshold=0.7,
        )

    def test_unsupported_judge_type_raises_error(self, mock_deepeval_metrics):
        """Test that unsupported judge type raises JudgeError."""
        config = JudgeConfig(
            name="unsupported",
            type="deepeval.unknown",
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


class TestGEvalExpectedOutputTemplate:
    """Test GEval custom expected_output_template support."""

    def test_expected_output_template_rendering(
        self, mock_deepeval_metrics, geval_config_with_template, mock_scenario
    ):
        """Test that expected_output_template is rendered with scenario context."""
        # Create a scenario with template variables
        scenario_with_vars = Scenario(
            id="geography",
            input={
                "text": "What is the capital of France?",
                "country": "France",
                "capital": "Paris",
            },
            expected_behavior="Paris",
        )

        judge = DeepEvalJudge(geval_config_with_template)

        # Get expected output via _get_expected_output
        expected = judge._get_expected_output(scenario_with_vars)

        # Verify template was rendered correctly
        assert expected == "The capital of France is Paris"
        assert "{{" not in expected, "Template should be fully rendered"

    def test_expected_output_template_with_test_case(
        self, mock_deepeval_metrics, geval_config_with_template
    ):
        """Test that expected_output_template is used in test case creation."""
        scenario_with_vars = Scenario(
            id="geography",
            input={
                "text": "What is the capital?",
                "country": "France",
                "capital": "Paris",
            },
        )

        judge = DeepEvalJudge(geval_config_with_template)
        test_case = judge._create_test_case(scenario_with_vars, "Paris")

        # Verify expected_output was set to rendered template
        assert test_case.expected_output == "The capital of France is Paris"
        assert test_case.input == "What is the capital?"
        assert test_case.actual_output == "Paris"

    def test_expected_output_fallback_to_scenario(
        self, mock_deepeval_metrics, geval_config_with_template, mock_scenario
    ):
        """Test fallback to scenario.expected when no template variables."""
        # Scenario without template variables - should use scenario.expected
        judge = DeepEvalJudge(geval_config_with_template)
        expected = judge._get_expected_output(mock_scenario)

        # Should fall back to scenario.expected_behavior
        assert expected == mock_scenario.expected_behavior
        assert expected == "Paris"

    def test_geval_without_template(
        self, mock_deepeval_metrics, geval_config, mock_scenario
    ):
        """Test GEval judge works without expected_output_template."""
        judge = DeepEvalJudge(geval_config)
        expected = judge._get_expected_output(mock_scenario)

        # Should use scenario.expected_behavior
        assert expected == "Paris"
