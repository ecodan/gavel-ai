"""Unit tests for config loading and validation."""
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import toml
import yaml

from gavel_ai.core.config.loader import load_config
from gavel_ai.core.config.models import AsyncConfig, EvalConfig
from gavel_ai.core.exceptions import ConfigError, ValidationError


class TestLoadConfig:
    """Test suite for config loader functionality."""

    def test_load_valid_json_config(self, tmp_path: Path) -> None:
        """Test loading a valid JSON config file."""
        config_data: Dict[str, Any] = {
            "eval_name": "test_eval",
            "eval_type": "local",
            "processor_type": "prompt_input",
            "scenarios_file": "data/scenarios.json",
            "agents_file": "config/agents.json",
            "judges_config": "config/judges/",
            "output_dir": "runs/",
        }

        config_file = tmp_path / "eval_config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = load_config(config_file, EvalConfig)

        assert config.eval_name == "test_eval"
        assert config.eval_type == "local"
        assert config.processor_type == "prompt_input"

    def test_load_valid_yaml_config(self, tmp_path: Path) -> None:
        """Test loading a valid YAML config file."""
        config_data: Dict[str, Any] = {
            "max_workers": 4,
            "timeout_seconds": 30,
            "retry_count": 3,
            "error_handling": "fail_fast",
        }

        config_file = tmp_path / "async_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(config_file, AsyncConfig)

        assert config.max_workers == 4
        assert config.timeout_seconds == 30
        assert config.retry_count == 3

    def test_load_valid_toml_config(self, tmp_path: Path) -> None:
        """Test loading a valid TOML config file."""
        config_data: Dict[str, Any] = {
            "max_workers": 8,
            "timeout_seconds": 60,
            "retry_count": 5,
            "error_handling": "continue",
        }

        config_file = tmp_path / "async_config.toml"
        with open(config_file, "w") as f:
            toml.dump(config_data, f)

        config = load_config(config_file, AsyncConfig)

        assert config.max_workers == 8
        assert config.timeout_seconds == 60

    def test_missing_config_file(self, tmp_path: Path) -> None:
        """Test that ConfigError is raised for missing config file."""
        config_file = tmp_path / "nonexistent.json"

        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file, EvalConfig)

        assert "not found" in str(exc_info.value).lower()
        assert "Create file or check path" in str(exc_info.value)

    def test_invalid_json_syntax(self, tmp_path: Path) -> None:
        """Test that ConfigError is raised for invalid JSON syntax."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{invalid json}")

        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file, EvalConfig)

        assert "invalid" in str(exc_info.value).lower() or "parse" in str(
            exc_info.value
        ).lower()

    def test_missing_required_field(self, tmp_path: Path) -> None:
        """Test that ValidationError is raised for missing required fields."""
        config_data: Dict[str, Any] = {
            "eval_name": "test_eval",
            # Missing other required fields
        }

        config_file = tmp_path / "incomplete.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        with pytest.raises(ValidationError) as exc_info:
            load_config(config_file, EvalConfig)

        error_msg = str(exc_info.value).lower()
        assert "validation" in error_msg or "required" in error_msg

    def test_type_mismatch(self, tmp_path: Path) -> None:
        """Test that ValidationError is raised for type mismatches."""
        config_data: Dict[str, Any] = {
            "max_workers": "four",  # Should be int
            "timeout_seconds": 30,
            "retry_count": 3,
            "error_handling": "fail_fast",
        }

        config_file = tmp_path / "type_error.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        with pytest.raises(ValidationError) as exc_info:
            load_config(config_file, AsyncConfig)

        error_msg = str(exc_info.value).lower()
        assert "validation" in error_msg or "type" in error_msg or "int" in error_msg

    def test_forward_compatibility_unknown_fields(self, tmp_path: Path) -> None:
        """Test that unknown fields are silently ignored (forward compatible)."""
        config_data: Dict[str, Any] = {
            "eval_name": "test_eval",
            "eval_type": "local",
            "processor_type": "prompt_input",
            "scenarios_file": "data/scenarios.json",
            "agents_file": "config/agents.json",
            "judges_config": "config/judges/",
            "output_dir": "runs/",
            "future_feature_flag": True,  # Unknown field
            "new_v2_setting": "value",  # Unknown field
        }

        config_file = tmp_path / "forward_compat.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Should not raise exception, unknown fields silently ignored
        config = load_config(config_file, EvalConfig)

        assert config.eval_name == "test_eval"
        # Unknown fields should not be accessible
        assert not hasattr(config, "future_feature_flag")
        assert not hasattr(config, "new_v2_setting")

    def test_environment_variable_substitution(self, tmp_path: Path) -> None:
        """Test that {{VAR_NAME}} is substituted with environment variables."""
        # Set environment variable
        os.environ["TEST_API_KEY"] = "sk-test-key-12345"

        config_data: Dict[str, Any] = {
            "eval_name": "test_eval",
            "eval_type": "local",
            "processor_type": "prompt_input",
            "scenarios_file": "data/scenarios.json",
            "agents_file": "{{TEST_API_KEY}}",  # Should be substituted
            "judges_config": "config/judges/",
            "output_dir": "runs/",
        }

        config_file = tmp_path / "env_vars.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = load_config(config_file, EvalConfig)

        assert config.agents_file == "sk-test-key-12345"

        # Cleanup
        del os.environ["TEST_API_KEY"]

    def test_missing_environment_variable(self, tmp_path: Path) -> None:
        """Test that ConfigError is raised for missing environment variables."""
        config_data: Dict[str, Any] = {
            "eval_name": "test_eval",
            "eval_type": "local",
            "processor_type": "prompt_input",
            "scenarios_file": "data/scenarios.json",
            "agents_file": "{{MISSING_ENV_VAR}}",  # Not set
            "judges_config": "config/judges/",
            "output_dir": "runs/",
        }

        config_file = tmp_path / "missing_env.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file, EvalConfig)

        error_msg = str(exc_info.value)
        assert "MISSING_ENV_VAR" in error_msg
        assert "not set" in error_msg.lower()

    def test_no_env_substitution_when_disabled(self, tmp_path: Path) -> None:
        """Test that env vars are not substituted when substitute_env=False."""
        config_data: Dict[str, Any] = {
            "eval_name": "test_eval",
            "eval_type": "local",
            "processor_type": "prompt_input",
            "scenarios_file": "data/scenarios.json",
            "agents_file": "{{SOME_VAR}}",  # Should NOT be substituted
            "judges_config": "config/judges/",
            "output_dir": "runs/",
        }

        config_file = tmp_path / "no_sub.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = load_config(config_file, EvalConfig, substitute_env=False)

        assert config.agents_file == "{{SOME_VAR}}"  # Not substituted

    def test_unsupported_file_format(self, tmp_path: Path) -> None:
        """Test that ConfigError is raised for unsupported file formats."""
        config_file = tmp_path / "config.xml"
        config_file.write_text("<config>data</config>")

        with pytest.raises(ConfigError) as exc_info:
            load_config(config_file, EvalConfig)

        error_msg = str(exc_info.value)
        assert "unsupported" in error_msg.lower() or "format" in error_msg.lower()
        assert ".xml" in error_msg or "xml" in error_msg.lower()


class TestConfigModels:
    """Test suite for Pydantic config models."""

    def test_eval_config_has_extra_ignore(self) -> None:
        """Test that EvalConfig uses extra='ignore' for forward compatibility."""
        config_dict = {
            "eval_name": "test",
            "eval_type": "local",
            "processor_type": "prompt_input",
            "scenarios_file": "data/scenarios.json",
            "agents_file": "config/agents.json",
            "judges_config": "config/judges/",
            "output_dir": "runs/",
            "unknown_field": "should_be_ignored",
        }

        # Should not raise validation error
        config = EvalConfig.model_validate(config_dict)

        assert config.eval_name == "test"
        assert not hasattr(config, "unknown_field")

    def test_async_config_has_extra_ignore(self) -> None:
        """Test that AsyncConfig uses extra='ignore' for forward compatibility."""
        config_dict = {
            "max_workers": 4,
            "timeout_seconds": 30,
            "retry_count": 3,
            "error_handling": "fail_fast",
            "future_feature": True,
        }

        # Should not raise validation error
        config = AsyncConfig.model_validate(config_dict)

        assert config.max_workers == 4
        assert not hasattr(config, "future_feature")

    def test_async_config_defaults(self) -> None:
        """Test that AsyncConfig has sensible defaults."""
        config = AsyncConfig()

        assert config.max_workers == 4
        assert config.timeout_seconds == 30
        assert config.retry_count == 3
        assert config.error_handling == "fail_fast"
