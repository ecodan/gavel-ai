import pytest

pytestmark = pytest.mark.unit
"""Unit tests for config loading and validation using new storage abstraction.

Tests the StructDataSource and config model functionality that replaced
the old ConfigLoader.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

import pytest
import toml
import yaml

from gavel_ai.core.adapters.backends import InMemoryStorageBackend, LocalStorageBackend
from gavel_ai.core.adapters.data_sources import StructDataSource
from gavel_ai.models.config import AsyncConfig, EvalConfig


class TestStructDataSource:
    """Test suite for StructDataSource config loading functionality."""

    def test_load_valid_json_config(self, tmp_path: Path) -> None:
        """Test loading a valid JSON config file."""
        config_data: Dict[str, Any] = {
            "eval_name": "test_eval",
            "eval_type": "oneshot",
            "test_subject_type": "local",
            "test_subjects": [{"prompt_name": "default", "judges": []}],
            "variants": ["test"],
            "scenarios": {"source": "file.local", "name": "scenarios.json"},
        }

        config_file = tmp_path / "eval_config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        storage = LocalStorageBackend(tmp_path)
        source = StructDataSource(storage, "eval_config.json", schema=EvalConfig)
        config = source.read()

        assert config.eval_name == "test_eval"
        assert config.eval_type == "oneshot"
        assert config.test_subject_type == "local"

    def test_load_valid_yaml_config(self, tmp_path: Path) -> None:
        """Test loading a valid YAML config file."""
        config_data: Dict[str, Any] = {
            "num_workers": 4,
            "arrival_rate_per_sec": 20.0,
            "exec_rate_per_min": 100,
            "max_retries": 3,
            "task_timeout_seconds": 300,
            "stuck_timeout_seconds": 600,
            "emit_progress_interval_sec": 10,
        }

        config_file = tmp_path / "async_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        storage = LocalStorageBackend(tmp_path)
        source = StructDataSource(storage, "async_config.yaml", schema=AsyncConfig)
        config = source.read()

        assert config.num_workers == 4
        assert config.arrival_rate_per_sec == 20.0
        assert config.max_retries == 3

    def test_load_valid_toml_config(self, tmp_path: Path) -> None:
        """Test loading a valid TOML config file."""
        config_data: Dict[str, Any] = {
            "num_workers": 8,
            "arrival_rate_per_sec": 15.0,
            "exec_rate_per_min": 50,
            "max_retries": 5,
            "task_timeout_seconds": 600,
            "stuck_timeout_seconds": 1200,
            "emit_progress_interval_sec": 20,
        }

        config_file = tmp_path / "async_config.toml"
        with open(config_file, "w") as f:
            toml.dump(config_data, f)

        storage = LocalStorageBackend(tmp_path)
        source = StructDataSource(storage, "async_config.toml", schema=AsyncConfig)
        config = source.read()

        assert config.num_workers == 8
        assert config.arrival_rate_per_sec == 15.0

    def test_missing_config_file(self, tmp_path: Path) -> None:
        """Test that FileNotFoundError is raised for missing config file."""
        storage = LocalStorageBackend(tmp_path)
        source = StructDataSource(storage, "nonexistent.json", schema=EvalConfig)

        with pytest.raises(FileNotFoundError):
            source.read()

    def test_invalid_json_syntax(self, tmp_path: Path) -> None:
        """Test that JSONDecodeError is raised for invalid JSON syntax."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{invalid json}")

        storage = LocalStorageBackend(tmp_path)
        source = StructDataSource(storage, "invalid.json", schema=EvalConfig)

        with pytest.raises(json.JSONDecodeError):
            source.read()

    def test_missing_required_field(self, tmp_path: Path) -> None:
        """Test that ValidationError is raised for missing required fields."""
        config_data: Dict[str, Any] = {
            "eval_name": "test_eval",
            # Missing other required fields
        }

        config_file = tmp_path / "incomplete.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        storage = LocalStorageBackend(tmp_path)
        source = StructDataSource(storage, "incomplete.json", schema=EvalConfig)

        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            source.read()

    def test_type_mismatch(self, tmp_path: Path) -> None:
        """Test that ValidationError is raised for type mismatches."""
        config_data: Dict[str, Any] = {
            "num_workers": "four",  # Should be int
            "arrival_rate_per_sec": 20.0,
            "exec_rate_per_min": 100,
            "max_retries": 3,
            "task_timeout_seconds": 300,
            "stuck_timeout_seconds": 600,
            "emit_progress_interval_sec": 10,
        }

        config_file = tmp_path / "type_error.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        storage = LocalStorageBackend(tmp_path)
        source = StructDataSource(storage, "type_error.json", schema=AsyncConfig)

        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            source.read()

    def test_forward_compatibility_unknown_fields(self, tmp_path: Path) -> None:
        """Test that unknown fields are silently ignored (forward compatible)."""
        config_data: Dict[str, Any] = {
            "eval_name": "test_eval",
            "eval_type": "oneshot",
            "test_subject_type": "local",
            "test_subjects": [{"prompt_name": "default", "judges": []}],
            "variants": ["test"],
            "scenarios": {"source": "file.local", "name": "scenarios.json"},
            "future_feature_flag": True,  # Unknown field
            "new_v2_setting": "value",  # Unknown field
        }

        config_file = tmp_path / "forward_compat.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        storage = LocalStorageBackend(tmp_path)
        source = StructDataSource(storage, "forward_compat.json", schema=EvalConfig)

        # Should not raise exception, unknown fields silently ignored
        config = source.read()

        assert config.eval_name == "test_eval"
        # Unknown fields should not be accessible
        assert not hasattr(config, "future_feature_flag")
        assert not hasattr(config, "new_v2_setting")

    def test_unsupported_file_format(self, tmp_path: Path) -> None:
        """Test that ValueError is raised for unsupported file formats."""
        config_file = tmp_path / "config.xml"
        config_file.write_text("<config>data</config>")

        storage = LocalStorageBackend(tmp_path)
        source = StructDataSource(storage, "config.xml", schema=EvalConfig)

        with pytest.raises(ValueError, match="Unsupported struct format"):
            source.read()

    def test_in_memory_backend(self) -> None:
        """Test loading config from in-memory backend."""
        storage = InMemoryStorageBackend()

        config_data: Dict[str, Any] = {
            "num_workers": 4,
            "arrival_rate_per_sec": 20.0,
            "exec_rate_per_min": 100,
            "max_retries": 3,
            "task_timeout_seconds": 300,
            "stuck_timeout_seconds": 600,
            "emit_progress_interval_sec": 10,
        }

        storage.write_bytes("config.json", json.dumps(config_data).encode())
        source = StructDataSource(storage, "config.json", schema=AsyncConfig)
        config = source.read()

        assert config.num_workers == 4
        assert config.max_retries == 3

    def test_write_and_read_roundtrip(self, tmp_path: Path) -> None:
        """Test writing and reading a config file."""
        storage = LocalStorageBackend(tmp_path)
        source = StructDataSource(storage, "output.json", schema=AsyncConfig)

        config = AsyncConfig(
            num_workers=16,
            arrival_rate_per_sec=50.0,
            exec_rate_per_min=200,
            max_retries=5,
            task_timeout_seconds=600,
            stuck_timeout_seconds=1200,
            emit_progress_interval_sec=30,
        )

        source.write(config)
        loaded_config = source.read()

        assert loaded_config.num_workers == 16
        assert loaded_config.arrival_rate_per_sec == 50.0
        assert loaded_config.max_retries == 5


class TestConfigModels:
    """Test suite for Pydantic config models."""

    def test_eval_config_has_extra_ignore(self) -> None:
        """Test that EvalConfig uses extra='ignore' for forward compatibility."""
        config_dict = {
            "eval_name": "test",
            "eval_type": "oneshot",
            "test_subject_type": "local",
            "test_subjects": [{"prompt_name": "default", "judges": []}],
            "variants": ["test"],
            "scenarios": {"source": "file.local", "name": "scenarios.json"},
            "unknown_field": "should_be_ignored",
        }

        # Should not raise validation error
        config = EvalConfig.model_validate(config_dict)

        assert config.eval_name == "test"
        assert not hasattr(config, "unknown_field")

    def test_async_config_has_extra_ignore(self) -> None:
        """Test that AsyncConfig uses extra='ignore' for forward compatibility."""
        config_dict = {
            "num_workers": 4,
            "arrival_rate_per_sec": 20.0,
            "exec_rate_per_min": 100,
            "max_retries": 3,
            "task_timeout_seconds": 300,
            "stuck_timeout_seconds": 600,
            "emit_progress_interval_sec": 10,
            "future_feature": True,
        }

        # Should not raise validation error
        config = AsyncConfig.model_validate(config_dict)

        assert config.num_workers == 4
        assert not hasattr(config, "future_feature")

    def test_async_config_defaults(self) -> None:
        """Test that AsyncConfig has sensible defaults."""
        config = AsyncConfig()

        assert config.num_workers == 8
        assert config.arrival_rate_per_sec == 20.0
        assert config.max_retries == 3
