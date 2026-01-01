"""Integration tests for oneshot run CLI wiring.

Tests verify that all components are correctly wired together:
- Config loading
- Run context creation
- Component instantiation
- Error handling

Note: These tests mock the actual LLM calls to avoid needing API keys.
"""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import toml

from gavel_ai.core.config_loader import ConfigLoader
from gavel_ai.core.exceptions import ConfigError, ValidationError


class TestConfigLoaderIntegration:
    """Test ConfigLoader orchestration."""

    def test_load_all_configs_success(self, tmp_path: Path) -> None:
        """Test loading all config files successfully."""
        eval_root = tmp_path / "evaluations"
        eval_name = "test_eval"
        eval_dir = eval_root / eval_name

        # Create directory structure
        (eval_dir / "config").mkdir(parents=True)
        (eval_dir / "data").mkdir(parents=True)
        (eval_dir / "prompts").mkdir(parents=True)

        # Create eval_config.json
        eval_config_data = {
            "eval_name": "test_eval",
            "eval_type": "local",
            "processor_type": "prompt_input",
            "scenarios_file": "data/scenarios.json",
            "agents_file": "config/agents.json",
            "judges_config": "config/judges/",
            "output_dir": "runs/",
        }
        with open(eval_dir / "config" / "eval_config.json", "w") as f:
            json.dump(eval_config_data, f)

        # Create async_config.json
        async_config_data = {
            "max_workers": 4,
            "timeout_seconds": 30,
            "retry_count": 3,
            "error_handling": "fail_fast",
        }
        with open(eval_dir / "config" / "async_config.json", "w") as f:
            json.dump(async_config_data, f)

        # Create agents.json
        agents_data = {
            "_models": {
                "test-model": {
                    "model_provider": "anthropic",
                    "model_family": "claude",
                    "model_version": "claude-test",
                    "model_parameters": {"temperature": 0.7},
                    "provider_auth": {"api_key": "test-key"},
                }
            },
            "subject_agent": {"model_id": "test-model", "prompt": "default:v1"},
        }
        with open(eval_dir / "config" / "agents.json", "w") as f:
            json.dump(agents_data, f)

        # Create scenarios.json
        scenarios_data = {
            "scenarios": [
                {
                    "id": "s1",
                    "input": {"input": "test"},
                    "expected_behavior": "output",
                    "metadata": {},
                }
            ]
        }
        with open(eval_dir / "data" / "scenarios.json", "w") as f:
            json.dump(scenarios_data, f)

        # Create prompt template
        with open(eval_dir / "prompts" / "default.toml", "w") as f:
            f.write('v1 = "Test prompt: {{input}}"')

        # Test loading
        loader = ConfigLoader(eval_root, eval_name)

        eval_config = loader.load_eval_config()
        assert eval_config.eval_name == "test_eval"
        assert eval_config.processor_type == "prompt_input"

        async_config = loader.load_async_config()
        assert async_config.max_workers == 4

        agents_config = loader.load_agents_config()
        assert "_models" in agents_config
        assert "subject_agent" in agents_config

        scenarios = loader.load_scenarios()
        assert len(scenarios) == 1
        assert scenarios[0].id == "s1"

        prompt = loader.load_prompt_template()
        assert "Test prompt" in prompt

    def test_config_loader_missing_evaluation(self, tmp_path: Path) -> None:
        """Test error when evaluation doesn't exist."""
        eval_root = tmp_path / "evaluations"
        eval_name = "missing_eval"

        loader = ConfigLoader(eval_root, eval_name)

        with pytest.raises(ConfigError, match="Evaluation 'missing_eval' not found"):
            loader.load_eval_config()

    def test_config_loader_invalid_agents_json(self, tmp_path: Path) -> None:
        """Test error handling for invalid agents.json."""
        eval_root = tmp_path / "evaluations"
        eval_name = "test_eval"
        eval_dir = eval_root / eval_name
        (eval_dir / "config").mkdir(parents=True)

        # Create invalid JSON
        with open(eval_dir / "config" / "agents.json", "w") as f:
            f.write("{invalid json")

        loader = ConfigLoader(eval_root, eval_name)

        with pytest.raises(ConfigError, match="Invalid TOML|Invalid JSON"):
            loader.load_agents_config()

    def test_config_loader_missing_scenarios(self, tmp_path: Path) -> None:
        """Test error when scenarios file doesn't exist."""
        eval_root = tmp_path / "evaluations"
        eval_name = "test_eval"
        eval_dir = eval_root / eval_name
        (eval_dir / "data").mkdir(parents=True)

        loader = ConfigLoader(eval_root, eval_name)

        with pytest.raises(ConfigError, match="Scenarios file not found"):
            loader.load_scenarios()

    def test_config_loader_prompt_version_not_found(self, tmp_path: Path) -> None:
        """Test error when prompt version doesn't exist."""
        eval_root = tmp_path / "evaluations"
        eval_name = "test_eval"
        eval_dir = eval_root / eval_name
        (eval_dir / "prompts").mkdir(parents=True)

        # Create prompt with only v1
        with open(eval_dir / "prompts" / "default.toml", "w") as f:
            f.write('v1 = "Test prompt"')

        loader = ConfigLoader(eval_root, eval_name)

        with pytest.raises(ConfigError, match="Prompt version 'v2' not found"):
            loader.load_prompt_template("default:v2")


class TestRunContextCreation:
    """Test run context creation and directory structure."""

    def test_run_id_format(self) -> None:
        """Test run ID follows expected format."""
        from datetime import datetime, timezone

        run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

        # Verify format: run-YYYYMMDD-HHMMSS
        assert run_id.startswith("run-")
        parts = run_id.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 6  # HHMMSS

    def test_run_directory_structure(self) -> None:
        """Test run directory structure is created correctly."""
        from gavel_ai.storage.filesystem import LocalFilesystemRun

        run_id = "run-20251230-120000"
        eval_name = "test_eval"
        metadata = {"run_id": run_id}

        run = LocalFilesystemRun(
            run_id=run_id,
            eval_name=eval_name,
            metadata=metadata,
            base_dir=".gavel",
        )

        expected_dir = Path(".gavel/evaluations/test_eval/runs/run-20251230-120000")
        assert run.run_dir == expected_dir


class TestErrorHandling:
    """Test error handling and messages."""

    def test_config_error_message_format(self) -> None:
        """Test ConfigError messages follow required format."""
        error = ConfigError(
            "Config file not found: agents.json - Run 'gavel oneshot create' first"
        )

        error_str = str(error)
        assert "Config file not found" in error_str
        assert "Run 'gavel oneshot create' first" in error_str

    def test_validation_error_message_format(self) -> None:
        """Test ValidationError messages follow required format."""
        error = ValidationError(
            "Invalid agents.json - Field 'model_provider' is required"
        )

        error_str = str(error)
        assert "Invalid agents.json" in error_str
        assert "Field 'model_provider' is required" in error_str
