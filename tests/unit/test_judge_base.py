import pytest

pytestmark = pytest.mark.unit
"""
Unit tests for Judge base class and judge-related models.

Tests Story 4.1 acceptance criteria:
- Judge ABC with correct interface
- JudgeConfig Pydantic model
- JudgeResult Pydantic model with score (1-10), reasoning, evidence
- Scenario model with expected behavior
"""

import pytest
from pydantic import ValidationError

from gavel_ai.core.models import JudgeConfig, JudgeResult, Scenario
from gavel_ai.judges.base import Judge


class TestJudgeResult:
    """Test JudgeResult model."""

    def test_judge_result_creation(self):
        """Test creating a valid JudgeResult."""
        result = JudgeResult(
            score=8,
            reasoning="Response is accurate and well-formatted",
            evidence="Matches expected output pattern",
        )

        assert result.score == 8
        assert result.reasoning == "Response is accurate and well-formatted"
        assert result.evidence == "Matches expected output pattern"

    def test_judge_result_score_range_valid(self):
        """Test that scores 1-10 are valid."""
        for score in range(1, 11):
            result = JudgeResult(score=score)
            assert result.score == score

    def test_judge_result_score_below_range_raises_error(self):
        """Test that scores below 1 raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            JudgeResult(score=0)

        assert "greater than or equal to 1" in str(exc_info.value)

    def test_judge_result_score_above_range_raises_error(self):
        """Test that scores above 10 raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            JudgeResult(score=11)

        assert "less than or equal to 10" in str(exc_info.value)

    def test_judge_result_optional_fields(self):
        """Test that reasoning and evidence are optional."""
        result = JudgeResult(score=5)

        assert result.score == 5
        assert result.reasoning is None
        assert result.evidence is None

    def test_judge_result_extra_fields_ignored(self):
        """Test that extra fields are ignored (forward compatibility)."""
        result = JudgeResult(
            score=7,
            reasoning="Good response",
            unknown_field="should be ignored",
        )

        assert result.score == 7
        assert result.reasoning == "Good response"
        assert not hasattr(result, "unknown_field")


class TestJudgeConfig:
    """Test JudgeConfig model."""

    def test_judge_config_creation(self):
        """Test creating a valid JudgeConfig."""
        config = JudgeConfig(
            name="similarity",
            type="deepeval.similarity",
            threshold=0.8,
            config={"model": "claude-3-5-sonnet"},
        )

        assert config.name == "similarity"
        assert config.type == "deepeval.similarity"
        assert config.threshold == 0.8
        assert config.config == {"model": "claude-3-5-sonnet"}

    def test_judge_config_optional_fields(self):
        """Test that threshold and config are optional."""
        config = JudgeConfig(
            name="custom",
            type="custom",
        )

        assert config.name == "custom"
        assert config.type == "custom"
        assert config.threshold is None
        assert config.config is None

    def test_judge_config_extra_fields_ignored(self):
        """Test that extra fields are ignored (forward compatibility)."""
        config = JudgeConfig(
            name="test",
            type="test",
            unknown_field="ignored",
        )

        assert config.name == "test"
        assert not hasattr(config, "unknown_field")


class TestScenario:
    """Test Scenario model."""

    def test_scenario_creation(self):
        """Test creating a valid Scenario."""
        scenario = Scenario(
            id="scenario-1",
            input={"user_query": "What is the capital of France?"},
            expected_behavior="Accurate factual answer",
            metadata={"category": "geography"},
        )

        assert scenario.id == "scenario-1"
        assert scenario.input == {"user_query": "What is the capital of France?"}
        assert scenario.expected_behavior == "Accurate factual answer"
        assert scenario.metadata == {"category": "geography"}

    def test_scenario_optional_fields(self):
        """Test that expected_behavior and metadata are optional."""
        scenario = Scenario(
            id="scenario-2",
            input={"query": "test"},
        )

        assert scenario.id == "scenario-2"
        assert scenario.input == {"query": "test"}
        assert scenario.expected_behavior is None
        assert scenario.metadata == {}

    def test_scenario_extra_fields_ignored(self):
        """Test that extra fields are ignored (forward compatibility)."""
        scenario = Scenario(
            id="scenario-3",
            input={"data": "value"},
            unknown_field="ignored",
        )

        assert scenario.id == "scenario-3"
        assert not hasattr(scenario, "unknown_field")


class TestJudgeBaseClass:
    """Test Judge abstract base class."""

    def test_judge_is_abstract(self):
        """Test that Judge cannot be instantiated directly."""
        config = JudgeConfig(name="test", type="test")

        with pytest.raises(TypeError) as exc_info:
            Judge(config)

        assert "Can't instantiate abstract class" in str(exc_info.value)

    def test_judge_requires_evaluate_method(self):
        """Test that Judge subclass must implement evaluate()."""

        class IncompleteJudge(Judge):
            pass

        config = JudgeConfig(name="incomplete", type="incomplete")

        with pytest.raises(TypeError) as exc_info:
            IncompleteJudge(config)

        assert "Can't instantiate abstract class" in str(exc_info.value)
        assert "evaluate" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_judge_concrete_implementation(self):
        """Test that a concrete Judge implementation works correctly."""

        class ConcreteJudge(Judge):
            async def evaluate(self, scenario: Scenario, subject_output: str) -> JudgeResult:
                return JudgeResult(
                    score=8,
                    reasoning="Test evaluation",
                    evidence=f"Scenario: {scenario.id}, Output: {subject_output}",
                )

        config = JudgeConfig(name="concrete", type="test")
        judge = ConcreteJudge(config)

        assert judge.config == config
        assert hasattr(judge, "tracer")

        scenario = Scenario(id="test", input={"query": "test"})
        result = await judge.evaluate(scenario, "test output")

        assert isinstance(result, JudgeResult)
        assert result.score == 8
        assert result.reasoning == "Test evaluation"
        assert "Scenario: test" in result.evidence
        assert "Output: test output" in result.evidence
