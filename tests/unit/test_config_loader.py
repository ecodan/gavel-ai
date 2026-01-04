"""Unit tests for config loading and validation."""
import json
import os
from pathlib import Path
from typing import Any, Dict

import pytest
import toml
import yaml

from gavel_ai.core.config.loader import load_config
from gavel_ai.core.config.models import AsyncConfig, EvalConfig
from gavel_ai.core.config_loader import resolve_model_id
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


class TestResolveModelId:
    """Test suite for resolve_model_id() helper function."""

    def test_resolve_custom_model_id(self) -> None:
        """Test resolving custom model ID to actual model version."""
        agents_config: Dict[str, Any] = {
            "_models": {
                "claude_standard": {
                    "model_version": "claude-sonnet-4-5-20250929",
                    "model_provider": "anthropic",
                }
            }
        }

        result = resolve_model_id(agents_config, "claude_standard")
        assert result == "claude-sonnet-4-5-20250929"

    def test_resolve_multiple_custom_ids(self) -> None:
        """Test resolving multiple different custom model IDs."""
        agents_config: Dict[str, Any] = {
            "_models": {
                "claude_standard": {"model_version": "claude-sonnet-4-5-20250929"},
                "gpt_standard": {"model_version": "gpt-4o-2024-08-06"},
                "claude_creative": {"model_version": "claude-opus-4-1-20250805"},
            }
        }

        assert resolve_model_id(agents_config, "claude_standard") == "claude-sonnet-4-5-20250929"
        assert resolve_model_id(agents_config, "gpt_standard") == "gpt-4o-2024-08-06"
        assert resolve_model_id(agents_config, "claude_creative") == "claude-opus-4-1-20250805"

    def test_pass_through_standard_model_name(self) -> None:
        """Test that standard model names pass through unchanged."""
        agents_config: Dict[str, Any] = {"_models": {}}

        # Standard model names should pass through
        assert resolve_model_id(agents_config, "gpt-4o") == "gpt-4o"
        assert resolve_model_id(agents_config, "claude-sonnet-4-5-20250929") == "claude-sonnet-4-5-20250929"
        assert resolve_model_id(agents_config, "gemini-2.0-flash") == "gemini-2.0-flash"

    def test_pass_through_when_not_in_models(self) -> None:
        """Test that model IDs not in _models are passed through."""
        agents_config: Dict[str, Any] = {
            "_models": {
                "claude_standard": {"model_version": "claude-sonnet-4-5-20250929"}
            }
        }

        # Unknown custom ID should be passed through (assumed to be standard name)
        result = resolve_model_id(agents_config, "some-unknown-model")
        assert result == "some-unknown-model"

    def test_error_when_model_version_missing(self) -> None:
        """Test that ConfigError is raised when model_version field is missing."""
        agents_config: Dict[str, Any] = {
            "_models": {
                "claude_standard": {
                    # Missing model_version field
                    "model_provider": "anthropic"
                }
            }
        }

        with pytest.raises(ConfigError) as exc_info:
            resolve_model_id(agents_config, "claude_standard")

        error_msg = str(exc_info.value)
        assert "missing 'model_version'" in error_msg
        assert "claude_standard" in error_msg

    def test_error_when_model_version_empty(self) -> None:
        """Test that ConfigError is raised when model_version is empty string."""
        agents_config: Dict[str, Any] = {
            "_models": {
                "claude_standard": {
                    "model_version": "",  # Empty string is falsy
                    "model_provider": "anthropic",
                }
            }
        }

        with pytest.raises(ConfigError) as exc_info:
            resolve_model_id(agents_config, "claude_standard")

        error_msg = str(exc_info.value)
        assert "missing 'model_version'" in error_msg

    def test_error_when_model_version_none(self) -> None:
        """Test that ConfigError is raised when model_version is None."""
        agents_config: Dict[str, Any] = {
            "_models": {
                "claude_standard": {
                    "model_version": None,
                    "model_provider": "anthropic",
                }
            }
        }

        with pytest.raises(ConfigError) as exc_info:
            resolve_model_id(agents_config, "claude_standard")

        error_msg = str(exc_info.value)
        assert "missing 'model_version'" in error_msg

    def test_empty_models_dict(self) -> None:
        """Test handling of empty _models dict."""
        agents_config: Dict[str, Any] = {"_models": {}}

        # Should pass through unknown IDs
        result = resolve_model_id(agents_config, "any-model-id")
        assert result == "any-model-id"

    def test_missing_models_key(self) -> None:
        """Test handling when _models key is missing entirely."""
        agents_config: Dict[str, Any] = {"other_field": "value"}

        # Should pass through any model ID when _models is missing
        result = resolve_model_id(agents_config, "any-model")
        assert result == "any-model"

    def test_resolve_with_nested_config_fields(self) -> None:
        """Test resolving custom ID when model has nested config fields."""
        agents_config: Dict[str, Any] = {
            "_models": {
                "claude_standard": {
                    "model_version": "claude-sonnet-4-5-20250929",
                    "model_provider": "anthropic",
                    "model_family": "claude",
                    "model_parameters": {
                        "temperature": 0.7,
                        "max_tokens": 4096,
                    },
                    "provider_auth": {
                        "api_key": "{{ANTHROPIC_API_KEY}}",
                    },
                }
            }
        }

        result = resolve_model_id(agents_config, "claude_standard")
        assert result == "claude-sonnet-4-5-20250929"

    def test_case_sensitive_model_id_lookup(self) -> None:
        """Test that model ID lookup is case-sensitive."""
        agents_config: Dict[str, Any] = {
            "_models": {
                "claude_standard": {"model_version": "claude-sonnet-4-5-20250929"}
            }
        }

        # Different case should not match
        result = resolve_model_id(agents_config, "Claude_Standard")
        assert result == "Claude_Standard"  # Passed through, not resolved
