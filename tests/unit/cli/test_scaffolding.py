"""Unit tests for oneshot scaffolding templates using real tmp-dir output."""
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def scaffold(tmp_path: Path, eval_name: str = "my-eval", eval_type: str = "local", template: str = "default") -> Path:
    """Call generate_all_templates and return the eval root."""
    from gavel_ai.cli.scaffolding import generate_all_templates

    eval_root = tmp_path / "evaluations"
    generate_all_templates(eval_root, eval_name, eval_type, template)
    return eval_root


class TestScaffoldDefault:
    def test_default_creates_eval_config(self, tmp_path):
        eval_root = scaffold(tmp_path)
        cfg_file = eval_root / "my-eval" / "config" / "eval_config.json"
        assert cfg_file.exists()
        cfg = json.loads(cfg_file.read_text())
        assert cfg["test_subject_type"] == "local"

    def test_default_creates_prompt(self, tmp_path):
        eval_root = scaffold(tmp_path)
        prompt_file = eval_root / "my-eval" / "config" / "prompts" / "assistant.toml"
        assert prompt_file.exists()

    def test_default_creates_quality_judge_toml(self, tmp_path):
        eval_root = scaffold(tmp_path)
        judge_file = eval_root / "my-eval" / "config" / "judges" / "quality_judge.toml"
        assert judge_file.exists()


class TestScaffoldClassification:
    def test_classification_eval_config_has_classifier_judge(self, tmp_path):
        eval_root = scaffold(tmp_path, template="classification")
        cfg = json.loads(
            (eval_root / "my-eval" / "config" / "eval_config.json").read_text()
        )
        judges = cfg["test_subjects"][0]["judges"]
        assert any(j["type"] == "classifier" for j in judges)

    def test_classification_scenarios_file_exists(self, tmp_path):
        eval_root = scaffold(tmp_path, template="classification")
        scenarios = json.loads(
            (eval_root / "my-eval" / "data" / "scenarios.json").read_text()
        )
        assert len(scenarios) == 3

    def test_classification_creates_classifier_prompt(self, tmp_path):
        eval_root = scaffold(tmp_path, template="classification")
        prompt_file = eval_root / "my-eval" / "config" / "prompts" / "classifier.toml"
        assert prompt_file.exists()


class TestScaffoldRegression:
    def test_regression_eval_config_has_regression_judge(self, tmp_path):
        eval_root = scaffold(tmp_path, template="regression")
        cfg = json.loads(
            (eval_root / "my-eval" / "config" / "eval_config.json").read_text()
        )
        judges = cfg["test_subjects"][0]["judges"]
        assert any(j["type"] == "regression" for j in judges)

    def test_regression_creates_regressor_prompt(self, tmp_path):
        eval_root = scaffold(tmp_path, template="regression")
        prompt_file = eval_root / "my-eval" / "config" / "prompts" / "regressor.toml"
        assert prompt_file.exists()


class TestScaffoldInSitu:
    def test_insitu_eval_config_test_subject_type(self, tmp_path):
        eval_root = scaffold(tmp_path, eval_type="in-situ")
        cfg = json.loads(
            (eval_root / "my-eval" / "config" / "eval_config.json").read_text()
        )
        assert cfg["test_subject_type"] == "in-situ"

    def test_insitu_no_prompt_toml(self, tmp_path):
        """in-situ scaffold creates no prompt TOML files (remote subjects have no local prompts)."""
        eval_root = scaffold(tmp_path, eval_type="in-situ")
        prompts_dir = eval_root / "my-eval" / "config" / "prompts"
        toml_files = list(prompts_dir.glob("*.toml")) if prompts_dir.exists() else []
        assert toml_files == []

    def test_insitu_test_subject_has_system_id(self, tmp_path):
        eval_root = scaffold(tmp_path, eval_type="in-situ")
        cfg = json.loads(
            (eval_root / "my-eval" / "config" / "eval_config.json").read_text()
        )
        subject = cfg["test_subjects"][0]
        assert "system_id" in subject


class TestScaffoldUnknownTemplate:
    def test_unknown_template_raises_config_error(self, tmp_path):
        from gavel_ai.core.exceptions import ConfigError

        with pytest.raises(ConfigError, match="Unknown template"):
            scaffold(tmp_path, template="nonexistent-template")
