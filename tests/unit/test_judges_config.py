import pytest

pytestmark = pytest.mark.unit
"""Unit tests for judges configuration models."""

from typing import Any, Dict

import pytest

from gavel_ai.models.config import GEvalConfig, JudgeConfig


class TestJudgeConfigModel:
    """Test suite for JudgeConfig Pydantic model."""

    def test_parse_basic_judge(self) -> None:
        """Test parsing basic judge configuration."""
        judge_data: Dict[str, Any] = {
            "name": "similarity",
            "type": "deepeval.similarity",
            "config": {"threshold": 0.8},
        }

        judge = JudgeConfig.model_validate(judge_data)

        assert judge.name == "similarity"
        assert judge.type == "deepeval.similarity"
        assert judge.config == {"threshold": 0.8}

    def test_parse_judge_with_config_ref(self) -> None:
        """Test parsing judge with external config reference."""
        judge_data: Dict[str, Any] = {
            "name": "custom_accuracy",
            "type": "deepeval.geval",
            "config_ref": "judges/custom_accuracy.json",
        }

        judge = JudgeConfig.model_validate(judge_data)

        assert judge.config_ref == "judges/custom_accuracy.json"

    def test_judge_config_has_extra_ignore(self) -> None:
        """Test that JudgeConfig ignores unknown fields."""
        judge_data: Dict[str, Any] = {
            "name": "similarity",
            "type": "deepeval.similarity",
            "future_field": "ignored",
        }

        judge = JudgeConfig.model_validate(judge_data)

        assert judge.name == "similarity"
        assert not hasattr(judge, "future_field")

    def test_judge_with_threshold(self) -> None:
        """Test parsing judge with threshold."""
        judge_data: Dict[str, Any] = {
            "name": "similarity",
            "type": "deepeval.similarity",
            "threshold": 0.8,
        }

        judge = JudgeConfig.model_validate(judge_data)

        assert judge.threshold == 0.8

    def test_judge_with_model(self) -> None:
        """Test parsing judge with model specification."""
        judge_data: Dict[str, Any] = {
            "name": "geval_custom",
            "type": "deepeval.geval",
            "model": "claude-3-5-sonnet-latest",
        }

        judge = JudgeConfig.model_validate(judge_data)

        assert judge.model == "claude-3-5-sonnet-latest"

    def test_judge_with_geval_fields(self) -> None:
        """Test parsing judge with GEval-specific fields."""
        judge_data: Dict[str, Any] = {
            "name": "custom",
            "type": "deepeval.geval",
            "criteria": "Technical accuracy",
            "evaluation_steps": ["Check facts", "Verify code"],
        }

        judge = JudgeConfig.model_validate(judge_data)

        assert judge.criteria == "Technical accuracy"
        assert judge.evaluation_steps == ["Check facts", "Verify code"]


class TestGEvalConfigModel:
    """Test suite for GEvalConfig Pydantic model."""

    def test_parse_geval_config(self) -> None:
        """Test parsing custom GEval configuration."""
        geval_data: Dict[str, Any] = {
            "criteria": "Technical accuracy",
            "evaluation_steps": ["Check facts", "Verify code"],
            "model": "claude-3-5-sonnet-latest",
            "threshold": 0.7,
        }

        geval = GEvalConfig.model_validate(geval_data)

        assert geval.criteria == "Technical accuracy"
        assert len(geval.evaluation_steps) == 2
        assert geval.model == "claude-3-5-sonnet-latest"
        assert geval.threshold == 0.7

    def test_geval_threshold_validation(self) -> None:
        """Test that GEvalConfig validates threshold range."""
        # Should accept valid threshold
        valid_data: Dict[str, Any] = {
            "criteria": "Test",
            "evaluation_steps": ["Step 1"],
            "model": "claude",
            "threshold": 0.5,
        }
        geval = GEvalConfig.model_validate(valid_data)
        assert geval.threshold == 0.5

        # Should reject threshold > 1.0
        from pydantic import ValidationError

        invalid_data: Dict[str, Any] = {
            "criteria": "Test",
            "evaluation_steps": ["Step 1"],
            "model": "claude",
            "threshold": 1.5,
        }
        with pytest.raises(ValidationError):
            GEvalConfig.model_validate(invalid_data)

    def test_geval_default_threshold(self) -> None:
        """Test that GEvalConfig has default threshold."""
        geval_data: Dict[str, Any] = {
            "criteria": "Test criteria",
            "evaluation_steps": ["Step 1"],
            "model": "claude",
        }

        geval = GEvalConfig.model_validate(geval_data)

        assert geval.threshold == 0.7  # Default value


class TestDeepEvalJudgeTypes:
    """Test suite for all supported DeepEval judge types."""

    def test_similarity_judge(self) -> None:
        """Test similarity judge configuration."""
        judge = JudgeConfig(
            name="similarity",
            type="deepeval.similarity",
            config={"threshold": 0.8},
        )

        assert judge.type == "deepeval.similarity"
        assert judge.name == "similarity"

    def test_faithfulness_judge(self) -> None:
        """Test faithfulness judge configuration."""
        judge = JudgeConfig(
            name="faithfulness",
            type="deepeval.faithfulness",
            config={"threshold": 0.7},
        )

        assert judge.type == "deepeval.faithfulness"

    def test_hallucination_judge(self) -> None:
        """Test hallucination judge configuration."""
        judge = JudgeConfig(
            name="hallucination",
            type="deepeval.hallucination",
            config={"threshold": 0.9},
        )

        assert judge.type == "deepeval.hallucination"

    def test_geval_custom_judge(self) -> None:
        """Test custom GEval judge configuration."""
        judge = JudgeConfig(
            name="custom_accuracy",
            type="deepeval.geval",
            config={
                "criteria": "Technical accuracy",
                "evaluation_steps": ["Check facts", "Verify code"],
                "model": "claude-3-5-sonnet-latest",
                "threshold": 0.7,
            },
        )

        assert judge.type == "deepeval.geval"
        assert judge.name == "custom_accuracy"
        assert judge.config["criteria"] == "Technical accuracy"

    def test_answer_relevancy_judge(self) -> None:
        """Test answer relevancy judge configuration."""
        judge = JudgeConfig(
            name="relevancy",
            type="deepeval.answer_relevancy",
            threshold=0.7,
        )

        assert judge.type == "deepeval.answer_relevancy"

    def test_contextual_precision_judge(self) -> None:
        """Test contextual precision judge configuration."""
        judge = JudgeConfig(
            name="precision",
            type="deepeval.contextual_precision",
            threshold=0.7,
        )

        assert judge.type == "deepeval.contextual_precision"

    def test_contextual_recall_judge(self) -> None:
        """Test contextual recall judge configuration."""
        judge = JudgeConfig(
            name="recall",
            type="deepeval.contextual_recall",
            threshold=0.7,
        )

        assert judge.type == "deepeval.contextual_recall"
