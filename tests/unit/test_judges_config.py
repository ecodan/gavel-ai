"""Unit tests for judges configuration."""
import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from gavel_ai.core.config.judges import (
    load_judge_config,
    validate_judge_type,
    validate_judge_ids,
)
from gavel_ai.core.config.models import EvalConfig, GEvalConfig, JudgeConfig
from gavel_ai.core.exceptions import JudgeError


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
        invalid_data: Dict[str, Any] = {
            "criteria": "Test",
            "evaluation_steps": ["Step 1"],
            "model": "claude",
            "threshold": 1.5,
        }
        with pytest.raises(Exception):  # Pydantic validation error
            GEvalConfig.model_validate(invalid_data)


class TestEvalConfigWithJudges:
    """Test suite for EvalConfig with judges array."""

    def test_eval_config_with_judges(self) -> None:
        """Test that EvalConfig can include judges array."""
        config_data: Dict[str, Any] = {
            "eval_name": "test_eval",
            "eval_type": "local",
            "processor_type": "prompt_input",
            "scenarios_file": "data/scenarios.json",
            "agents_file": "config/agents.json",
            "judges_config": "config/judges/",
            "output_dir": "runs/",
            "judges": [
                {
                    "name": "similarity",
                    "type": "deepeval.similarity",
                    "config": {"threshold": 0.8},
                }
            ],
        }

        config = EvalConfig.model_validate(config_data)

        assert config.judges is not None
        assert len(config.judges) == 1
        assert config.judges[0].name == "similarity"


class TestJudgeConfigLoading:
    """Test suite for loading external judge configs."""

    def test_load_judge_config_without_config_ref(self) -> None:
        """Test loading judge without external config reference."""
        judge = JudgeConfig(
            name="similarity",
            type="deepeval.similarity",
            config={"threshold": 0.8},
        )

        # Should return unchanged
        loaded = load_judge_config(judge, Path("."))

        assert loaded.name == "similarity"
        assert loaded.config == {"threshold": 0.8}

    def test_load_judge_config_with_config_ref(self, tmp_path: Path) -> None:
        """Test loading and merging external judge config."""
        # Create external config file
        judges_dir = tmp_path / "config" / "judges"
        judges_dir.mkdir(parents=True)

        external_config = {
            "criteria": "Technical accuracy",
            "evaluation_steps": ["Check facts"],
            "model": "claude-3-5-sonnet-latest",
            "threshold": 0.7,
        }

        config_file = judges_dir / "custom.json"
        with open(config_file, "w") as f:
            json.dump(external_config, f)

        # Create judge with config_ref
        judge = JudgeConfig(
            name="custom",
            type="deepeval.geval",
            config={"threshold": 0.5},  # Should be overridden
            config_ref="config/judges/custom.json",
        )

        loaded = load_judge_config(judge, tmp_path)

        # External config should override inline config
        assert loaded.config["threshold"] == 0.7
        assert loaded.config["criteria"] == "Technical accuracy"

    def test_load_judge_config_missing_file(self, tmp_path: Path) -> None:
        """Test that JudgeError is raised for missing config file."""
        judge = JudgeConfig(
            name="custom",
            type="deepeval.geval",
            config_ref="config/judges/nonexistent.json",
        )

        with pytest.raises(JudgeError) as exc_info:
            load_judge_config(judge, tmp_path)

        assert "not found" in str(exc_info.value).lower()


class TestJudgeValidation:
    """Test suite for judge validation functions."""

    def test_validate_judge_ids_success(self) -> None:
        """Test successful validation when judge names are unique."""
        judges = [
            JudgeConfig(name="similarity", type="deepeval.similarity"),
            JudgeConfig(name="faithfulness", type="deepeval.faithfulness"),
        ]

        # Should not raise exception
        validate_judge_ids(judges)

    def test_validate_judge_ids_duplicate(self) -> None:
        """Test that JudgeError is raised for duplicate names."""
        judges = [
            JudgeConfig(name="similarity", type="deepeval.similarity"),
            JudgeConfig(name="similarity", type="deepeval.similarity"),  # Duplicate
        ]

        with pytest.raises(JudgeError) as exc_info:
            validate_judge_ids(judges)

        error_msg = str(exc_info.value)
        assert "duplicate" in error_msg.lower() or "unique" in error_msg.lower()

    def test_validate_deepeval_name_supported(self) -> None:
        """Test validation of supported judge types."""
        supported_names = [
            "deepeval.similarity",
            "deepeval.faithfulness",
            "deepeval.hallucination",
            "deepeval.answer_relevancy",
            "deepeval.contextual_precision",
            "deepeval.contextual_recall",
            "deepeval.geval",
        ]

        for name in supported_names:
            # Should not raise exception
            validate_judge_type(name)

    def test_validate_deepeval_name_unsupported(self) -> None:
        """Test that JudgeError is raised for unsupported judge types."""
        with pytest.raises(JudgeError) as exc_info:
            validate_judge_type("deepeval.invalid_judge")

        error_msg = str(exc_info.value)
        assert "unsupported" in error_msg.lower() or "invalid" in error_msg.lower()


class TestDeepEvalJudgeTypes:
    """Test suite for all supported DeepEval judge types."""

    def test_similarity_judge(self) -> None:
        """Test similarity judge configuration."""
        judge = JudgeConfig(
            name="similarity",
            type="deepeval.similarity",
            config={"threshold": 0.8},
        )

        validate_judge_type(judge.type)
        assert judge.type == "deepeval.similarity"

    def test_faithfulness_judge(self) -> None:
        """Test faithfulness judge configuration."""
        judge = JudgeConfig(
            name="faithfulness",
            type="deepeval.faithfulness",
            config={"threshold": 0.7},
        )

        validate_judge_type(judge.type)
        assert judge.type == "deepeval.faithfulness"

    def test_hallucination_judge(self) -> None:
        """Test hallucination judge configuration."""
        judge = JudgeConfig(
            name="hallucination",
            type="deepeval.hallucination",
            config={"threshold": 0.9},
        )

        validate_judge_type(judge.type)
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

        validate_judge_type(judge.type)
        assert judge.type == "deepeval.geval"
