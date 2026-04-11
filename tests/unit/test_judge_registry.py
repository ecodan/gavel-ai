import pytest

pytestmark = pytest.mark.unit
"""
Unit tests for JudgeRegistry.

Tests Story 4.4 acceptance criteria:
- Judges can be registered and instantiated by name
- JudgeRegistry.create() instantiates correct judge implementation
- Clear error messages when judge not found
- Auto-registration of DeepEval judges
"""

import pytest

from gavel_ai.core.exceptions import JudgeError
from gavel_ai.core.models import JudgeConfig, Scenario
from gavel_ai.judges import DeepEvalJudge, JudgeRegistry
from gavel_ai.judges.base import Judge


class TestJudgeRegistryBasics:
    """Test basic judge registry functionality."""

    def setup_method(self):
        """Clear registry before each test."""
        JudgeRegistry.clear()

    def teardown_method(self):
        """Restore default judges after each test."""
        JudgeRegistry.clear()
        # Re-register defaults by importing the module
        from gavel_ai.judges import _register_default_judges

        _register_default_judges()

    def test_register_judge(self):
        """Test registering a custom judge."""

        class CustomJudge(Judge):
            async def evaluate(self, scenario: Scenario, subject_output: str):
                pass

        JudgeRegistry.register("custom.test", CustomJudge)

        assert "custom.test" in JudgeRegistry.list_available()

    def test_register_duplicate_raises_error(self):
        """Test that registering duplicate judge type raises error."""

        class CustomJudge(Judge):
            async def evaluate(self, scenario: Scenario, subject_output: str):
                pass

        JudgeRegistry.register("custom.test", CustomJudge)

        with pytest.raises(JudgeError) as exc_info:
            JudgeRegistry.register("custom.test", CustomJudge)

        assert "already registered" in str(exc_info.value)
        assert "custom.test" in str(exc_info.value)

    def test_list_available_judges(self):
        """Test listing available judges."""

        class CustomJudge1(Judge):
            async def evaluate(self, scenario: Scenario, subject_output: str):
                pass

        class CustomJudge2(Judge):
            async def evaluate(self, scenario: Scenario, subject_output: str):
                pass

        JudgeRegistry.register("custom.test1", CustomJudge1)
        JudgeRegistry.register("custom.test2", CustomJudge2)

        available = JudgeRegistry.list_available()
        assert "custom.test1" in available
        assert "custom.test2" in available
        assert available == sorted(available)  # Should be sorted

    def test_clear_registry(self):
        """Test clearing the registry."""

        class CustomJudge(Judge):
            async def evaluate(self, scenario: Scenario, subject_output: str):
                pass

        JudgeRegistry.register("custom.test", CustomJudge)
        assert JudgeRegistry.list_available()

        JudgeRegistry.clear()
        assert not JudgeRegistry.list_available()


class TestJudgeRegistryFactory:
    """Test judge factory functionality."""

    def setup_method(self):
        """Ensure default judges are registered."""
        JudgeRegistry.clear()
        from gavel_ai.judges import _register_default_judges

        _register_default_judges()

    def test_create_judge_not_found(self, mock_deepeval_metrics):
        """Test creating judge with unknown type raises helpful error."""
        config = JudgeConfig(
            name="unknown",
            type="unknown.type",
        )

        with pytest.raises(JudgeError) as exc_info:
            JudgeRegistry.create(config)

        error_msg = str(exc_info.value)
        assert "not found in registry" in error_msg
        assert "unknown.type" in error_msg
        assert "Available types:" in error_msg

    def test_create_judge_from_registry(self, mock_deepeval_metrics):
        """Test creating judge from registry."""
        config = JudgeConfig(
            name="relevancy",
            type="deepeval.answer_relevancy",
            threshold=0.7,
        )

        judge = JudgeRegistry.create(config)

        assert isinstance(judge, DeepEvalJudge)
        assert judge.config == config

    def test_create_multiple_judge_types(self, mock_deepeval_metrics):
        """Test creating different judge types from registry."""
        configs = [
            JudgeConfig(name="relevancy", type="deepeval.answer_relevancy"),
            JudgeConfig(name="faithfulness", type="deepeval.faithfulness"),
            JudgeConfig(
                name="geval",
                type="deepeval.geval",
                model="gpt-4",  # GEval requires model
                criteria="Test criteria",
                evaluation_steps=["Step 1"],
            ),
        ]

        judges = [JudgeRegistry.create(config) for config in configs]

        assert all(isinstance(j, DeepEvalJudge) for j in judges)
        assert len(judges) == 3


class TestJudgeRegistryAutoRegistration:
    """Test auto-registration of default judges."""

    def test_deepeval_judges_auto_registered(self):
        """Test that DeepEval judges are auto-registered on import."""
        available = JudgeRegistry.list_available()

        # Should have all DeepEval judge types registered
        assert "deepeval.answer_relevancy" in available
        assert "deepeval.faithfulness" in available
        assert "deepeval.hallucination" in available
        assert "deepeval.geval" in available

    def test_auto_registered_judges_are_deepeval(self, mock_deepeval_metrics):
        """Test that auto-registered judges create DeepEvalJudge instances."""
        config = JudgeConfig(
            name="test",
            type="deepeval.faithfulness",
        )

        judge = JudgeRegistry.create(config)

        assert isinstance(judge, DeepEvalJudge)
        assert judge.config.type == "deepeval.faithfulness"
