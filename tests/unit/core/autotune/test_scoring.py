"""Unit tests for normalize_score: maps mixed judge scales to 0.0-1.0."""

import pytest

from gavel_ai.core.autotune.scoring import normalize_score

pytestmark = pytest.mark.unit


class TestNormalizeScore:
    @pytest.mark.parametrize(
        "judge_type",
        ["deepeval.geval", "deepeval.hallucination", "deepeval.answer_relevancy", "custom_llm_judge"],
    )
    def test_llm_judge_scores_divided_by_ten(self, judge_type: str) -> None:
        assert normalize_score(8, judge_type) == pytest.approx(0.8)
        assert normalize_score(10, judge_type) == pytest.approx(1.0)
        assert normalize_score(1, judge_type) == pytest.approx(0.1)

    @pytest.mark.parametrize("judge_type", ["classifier", "regression"])
    def test_deterministic_judge_scores_pass_through(self, judge_type: str) -> None:
        assert normalize_score(1, judge_type) == 1.0
        assert normalize_score(0, judge_type) == 0.0
        assert normalize_score(0.73, judge_type) == pytest.approx(0.73)
