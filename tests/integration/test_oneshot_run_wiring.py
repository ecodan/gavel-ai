"""Integration tests for oneshot run CLI wiring.

Tests verify that all components are correctly wired together:
- Config loading via LocalFileSystemEvalContext
- Run context creation
- Component instantiation
- Error handling

Note: These tests mock the actual LLM calls to avoid needing API keys.
"""

import json
from pathlib import Path

import pytest

from gavel_ai.core.contexts import LocalFileSystemEvalContext
from gavel_ai.core.exceptions import ConfigError, ResourceNotFoundError, ValidationError


class TestEvalContextIntegration:
    """Test LocalFileSystemEvalContext config loading."""

    def test_load_all_configs_success(self, tmp_path: Path) -> None:
        """Test loading all config files successfully."""
        eval_root = tmp_path / "evaluations"
        eval_name = "test_eval"
        eval_dir = eval_root / eval_name

        # Create directory structure
        (eval_dir / "config" / "prompts").mkdir(parents=True)
        (eval_dir / "config" / "judges").mkdir(parents=True)
        (eval_dir / "data").mkdir(parents=True)
        (eval_dir / "runs").mkdir(parents=True)

        # Create eval_config.json (new format with nested async)
        eval_config_data = {
            "eval_type": "oneshot",
            "test_subject_type": "local",
            "eval_name": "test_eval",
            "description": "Test evaluation",
            "test_subjects": [
                {
                    "prompt_name": "default",
                    "judges": [
                        {
                            "name": "quality",
                            "type": "deepeval.geval",
                            "config": {
                                "model": "test_model",
                                "criteria": "Evaluate quality",
                                "evaluation_steps": ["Step 1", "Step 2"],
                            },
                        }
                    ],
                }
            ],
            "variants": ["test_model"],
            "scenarios": {"source": "file.local", "name": "scenarios.json"},
            "execution": {"max_concurrent": 5},
            "async": {
                "num_workers": 4,
                "arrival_rate_per_sec": 20.0,
                "exec_rate_per_min": 100,
                "max_retries": 3,
                "task_timeout_seconds": 300,
                "stuck_timeout_seconds": 600,
                "emit_progress_interval_sec": 10,
            },
        }
        with open(eval_dir / "config" / "eval_config.json", "w") as f:
            json.dump(eval_config_data, f)

        # Create agents.json
        agents_data = {
            "_models": {
                "test_model": {
                    "model_provider": "anthropic",
                    "model_family": "claude",
                    "model_version": "claude-test",
                    "model_parameters": {"temperature": 0.7},
                    "provider_auth": {"api_key": "test-key"},
                }
            },
            "subject_agent": {"model_id": "test_model", "prompt": "default:v1"},
        }
        with open(eval_dir / "config" / "agents.json", "w") as f:
            json.dump(agents_data, f)

        # Create scenarios.json (root-level array)
        scenarios_data = [
            {
                "scenario_id": "s1",
                "input": "test input",
                "expected": "expected output",
                "metadata": {"category": "test"},
            }
        ]
        with open(eval_dir / "data" / "scenarios.json", "w") as f:
            json.dump(scenarios_data, f)

        # Create prompt template in config/prompts/
        with open(eval_dir / "config" / "prompts" / "default.toml", "w") as f:
            f.write('v1 = "Test prompt: {{input}}"')

        # Test loading via LocalFileSystemEvalContext
        ctx = LocalFileSystemEvalContext(eval_name, eval_root)

        eval_config = ctx.eval_config.read()
        assert eval_config.eval_name == "test_eval"
        assert eval_config.eval_type == "oneshot"
        assert eval_config.test_subject_type == "local"
        assert eval_config.async_config.num_workers == 4
        assert len(eval_config.test_subjects) == 1
        assert eval_config.test_subjects[0].prompt_name == "default"
        assert eval_config.variants == ["test_model"]

        agents_config = ctx.agents.read()
        assert "_models" in agents_config
        assert "subject_agent" in agents_config

        scenarios = ctx.scenarios.read()
        assert len(scenarios) == 1
        assert scenarios[0].scenario_id == "s1"

        prompt = ctx.get_prompt("default:v1")
        assert "Test prompt" in prompt

    def test_eval_context_missing_evaluation(self, tmp_path: Path) -> None:
        """Test error when evaluation doesn't exist."""
        eval_root = tmp_path / "evaluations"
        eval_name = "missing_eval"

        ctx = LocalFileSystemEvalContext(eval_name, eval_root)

        # Reading non-existent file should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            ctx.eval_config.read()

    def test_eval_context_invalid_agents_json(self, tmp_path: Path) -> None:
        """Test error handling for invalid agents.json."""
        eval_root = tmp_path / "evaluations"
        eval_name = "test_eval"
        eval_dir = eval_root / eval_name
        (eval_dir / "config").mkdir(parents=True)

        # Create invalid JSON
        with open(eval_dir / "config" / "agents.json", "w") as f:
            f.write("{invalid json")

        ctx = LocalFileSystemEvalContext(eval_name, eval_root)

        with pytest.raises(json.JSONDecodeError):
            ctx.agents.read()

    def test_eval_context_missing_scenarios(self, tmp_path: Path) -> None:
        """Test error when scenarios file doesn't exist."""
        eval_root = tmp_path / "evaluations"
        eval_name = "test_eval"
        eval_dir = eval_root / eval_name
        (eval_dir / "data").mkdir(parents=True)

        ctx = LocalFileSystemEvalContext(eval_name, eval_root)

        # Scenarios are read via iterator, empty if file doesn't exist
        scenarios = ctx.scenarios.read()
        assert scenarios == []

    def test_eval_context_prompt_version_not_found(self, tmp_path: Path) -> None:
        """Test error when prompt version doesn't exist."""
        eval_root = tmp_path / "evaluations"
        eval_name = "test_eval"
        eval_dir = eval_root / eval_name
        (eval_dir / "config" / "prompts").mkdir(parents=True)

        # Create prompt with only v1
        with open(eval_dir / "config" / "prompts" / "default.toml", "w") as f:
            f.write('v1 = "Test prompt"')

        ctx = LocalFileSystemEvalContext(eval_name, eval_root)

        with pytest.raises(ResourceNotFoundError, match="Version 'v2' not found"):
            ctx.get_prompt("default:v2")


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
        error = ConfigError("Config file not found: agents.json - Run 'gavel oneshot create' first")

        error_str = str(error)
        assert "Config file not found" in error_str
        assert "Run 'gavel oneshot create' first" in error_str

    def test_validation_error_message_format(self) -> None:
        """Test ValidationError messages follow required format."""
        error = ValidationError("Invalid agents.json - Field 'model_provider' is required")

        error_str = str(error)
        assert "Invalid agents.json" in error_str
        assert "Field 'model_provider' is required" in error_str
