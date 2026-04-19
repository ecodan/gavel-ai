import pytest

pytestmark = pytest.mark.unit
"""
Unit tests for the 4 new DeepEval judge types added in gavel-uplevel.

Tests:
- ToxicityMetric (deepeval.toxicity)
- ConversationCompletenessMetric (deepeval.conversation_completeness)
- ConversationalGEval (deepeval.conversational_geval)
- TurnRelevancyMetric (deepeval.turn_relevancy)
"""

from unittest.mock import MagicMock, patch

import pytest

from gavel_ai.core.exceptions import JudgeError
from gavel_ai.judges.deepeval_judge import DeepEvalJudge
from gavel_ai.judges.judge_registry import JudgeRegistry
from gavel_ai.models.runtime import JudgeConfig


@pytest.fixture()
def mock_new_deepeval_metrics():
    """
    Mock the 4 new DeepEval metric classes and patch JUDGE_TYPE_MAP to include them.
    """
    with (
        patch("gavel_ai.judges.deepeval_judge.ToxicityMetric") as mock_toxicity,
        patch(
            "gavel_ai.judges.deepeval_judge.ConversationCompletenessMetric"
        ) as mock_conv_completeness,
        patch("gavel_ai.judges.deepeval_judge.ConversationalGEval") as mock_conv_geval,
        patch("gavel_ai.judges.deepeval_judge.TurnRelevancyMetric") as mock_turn_relevancy,
    ):
        toxicity_instance = MagicMock()
        conv_completeness_instance = MagicMock()
        conv_geval_instance = MagicMock()
        turn_relevancy_instance = MagicMock()

        mock_toxicity.return_value = toxicity_instance
        mock_conv_completeness.return_value = conv_completeness_instance
        mock_conv_geval.return_value = conv_geval_instance
        mock_turn_relevancy.return_value = turn_relevancy_instance

        original_map = DeepEvalJudge.JUDGE_TYPE_MAP.copy()
        DeepEvalJudge.JUDGE_TYPE_MAP = {
            **original_map,
            "deepeval.toxicity": mock_toxicity,
            "deepeval.conversation_completeness": mock_conv_completeness,
            "deepeval.conversational_geval": mock_conv_geval,
            "deepeval.turn_relevancy": mock_turn_relevancy,
        }

        yield {
            "ToxicityMetric": mock_toxicity,
            "ConversationCompletenessMetric": mock_conv_completeness,
            "ConversationalGEval": mock_conv_geval,
            "TurnRelevancyMetric": mock_turn_relevancy,
            "toxicity_instance": toxicity_instance,
            "conv_completeness_instance": conv_completeness_instance,
            "conv_geval_instance": conv_geval_instance,
            "turn_relevancy_instance": turn_relevancy_instance,
        }

        DeepEvalJudge.JUDGE_TYPE_MAP = original_map


class TestJudgeTypeMapRegistration:
    """Test that all 4 new types are present in JUDGE_TYPE_MAP and JudgeRegistry."""

    def test_toxicity_in_judge_type_map(self) -> None:
        assert "deepeval.toxicity" in DeepEvalJudge.JUDGE_TYPE_MAP

    def test_conversation_completeness_in_judge_type_map(self) -> None:
        assert "deepeval.conversation_completeness" in DeepEvalJudge.JUDGE_TYPE_MAP

    def test_conversational_geval_in_judge_type_map(self) -> None:
        assert "deepeval.conversational_geval" in DeepEvalJudge.JUDGE_TYPE_MAP

    def test_turn_relevancy_in_judge_type_map(self) -> None:
        assert "deepeval.turn_relevancy" in DeepEvalJudge.JUDGE_TYPE_MAP

    def test_all_new_types_in_registry(self) -> None:
        available: list[str] = JudgeRegistry.list_available()
        assert "deepeval.toxicity" in available
        assert "deepeval.conversation_completeness" in available
        assert "deepeval.conversational_geval" in available
        assert "deepeval.turn_relevancy" in available


class TestToxicityMetricConstruction:
    """Test ToxicityMetric judge instantiation."""

    def test_toxicity_constructs_with_threshold(
        self, mock_new_deepeval_metrics: dict
    ) -> None:
        config = JudgeConfig(name="toxicity", type="deepeval.toxicity", threshold=0.9)
        judge = DeepEvalJudge(config)

        assert judge.metric == mock_new_deepeval_metrics["toxicity_instance"]
        mock_new_deepeval_metrics["ToxicityMetric"].assert_called_once_with(threshold=0.9)

    def test_toxicity_constructs_without_threshold(
        self, mock_new_deepeval_metrics: dict
    ) -> None:
        config = JudgeConfig(name="toxicity", type="deepeval.toxicity")
        judge = DeepEvalJudge(config)

        assert judge.metric == mock_new_deepeval_metrics["toxicity_instance"]


class TestConversationCompletenessConstruction:
    """Test ConversationCompletenessMetric judge instantiation."""

    def test_conversation_completeness_constructs_with_threshold(
        self, mock_new_deepeval_metrics: dict
    ) -> None:
        config = JudgeConfig(
            name="conv_completeness",
            type="deepeval.conversation_completeness",
            threshold=0.75,
        )
        judge = DeepEvalJudge(config)

        assert judge.metric == mock_new_deepeval_metrics["conv_completeness_instance"]
        mock_new_deepeval_metrics["ConversationCompletenessMetric"].assert_called_once_with(
            threshold=0.75
        )

    def test_conversation_completeness_constructs_without_threshold(
        self, mock_new_deepeval_metrics: dict
    ) -> None:
        config = JudgeConfig(
            name="conv_completeness", type="deepeval.conversation_completeness"
        )
        judge = DeepEvalJudge(config)

        assert judge.metric == mock_new_deepeval_metrics["conv_completeness_instance"]


class TestConversationalGEvalConstruction:
    """Test ConversationalGEval judge instantiation."""

    def test_conversational_geval_constructs_with_full_config(
        self, mock_new_deepeval_metrics: dict
    ) -> None:
        from unittest.mock import ANY

        mock_model = MagicMock()
        config = JudgeConfig(
            name="conv_quality",
            type="deepeval.conversational_geval",
            threshold=0.7,
            config={
                "model": "gpt-4",
                "criteria": "Evaluate conversation quality",
                "evaluation_steps": [
                    "Check goal completion",
                    "Evaluate coherence",
                ],
            },
        )
        with patch.object(DeepEvalJudge, "_create_model_instance", return_value=mock_model):
            judge = DeepEvalJudge(config)

        assert judge.metric == mock_new_deepeval_metrics["conv_geval_instance"]
        mock_new_deepeval_metrics["ConversationalGEval"].assert_called_once_with(
            name="conv_quality",
            criteria="Evaluate conversation quality",
            evaluation_steps=["Check goal completion", "Evaluate coherence"],
            model=mock_model,
            threshold=0.7,
        )

    def test_conversational_geval_requires_model(
        self, mock_new_deepeval_metrics: dict
    ) -> None:
        config = JudgeConfig(
            name="conv_quality",
            type="deepeval.conversational_geval",
            config={"criteria": "Evaluate quality"},
        )

        with pytest.raises(JudgeError, match="requires 'model' in config"):
            DeepEvalJudge(config)

    def test_conversational_geval_uses_default_criteria(
        self, mock_new_deepeval_metrics: dict
    ) -> None:
        from unittest.mock import ANY

        mock_model = MagicMock()
        config = JudgeConfig(
            name="conv_quality",
            type="deepeval.conversational_geval",
            config={"model": "gpt-4"},
        )
        with patch.object(DeepEvalJudge, "_create_model_instance", return_value=mock_model):
            DeepEvalJudge(config)

        mock_new_deepeval_metrics["ConversationalGEval"].assert_called_once_with(
            name="conv_quality",
            criteria="Evaluate the quality of the conversation",
            evaluation_steps=ANY,
            model=mock_model,
            threshold=0.5,
        )


class TestTurnRelevancyConstruction:
    """Test TurnRelevancyMetric judge instantiation."""

    def test_turn_relevancy_constructs_with_threshold(
        self, mock_new_deepeval_metrics: dict
    ) -> None:
        config = JudgeConfig(
            name="turn_relevancy", type="deepeval.turn_relevancy", threshold=0.8
        )
        judge = DeepEvalJudge(config)

        assert judge.metric == mock_new_deepeval_metrics["turn_relevancy_instance"]
        mock_new_deepeval_metrics["TurnRelevancyMetric"].assert_called_once_with(threshold=0.8)

    def test_turn_relevancy_constructs_without_threshold(
        self, mock_new_deepeval_metrics: dict
    ) -> None:
        config = JudgeConfig(name="turn_relevancy", type="deepeval.turn_relevancy")
        judge = DeepEvalJudge(config)

        assert judge.metric == mock_new_deepeval_metrics["turn_relevancy_instance"]
