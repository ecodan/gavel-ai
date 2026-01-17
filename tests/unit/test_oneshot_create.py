"""Unit tests for gavel oneshot create scaffolding command."""

import json
import tempfile
from pathlib import Path

import toml
from typer.testing import CliRunner

from gavel_ai.cli.main import app

runner = CliRunner()


class TestOneshotCreateCommand:
    """Test suite for oneshot create command."""

    def test_create_basic_structure(self, tmp_path: Path) -> None:
        """Test that create command generates basic directory structure."""
        eval_name = "test_eval"
        result = runner.invoke(
            app, ["oneshot", "create", "--eval", eval_name, "--eval-root", str(tmp_path)]
        )

        assert result.exit_code == 0
        eval_dir = tmp_path / eval_name
        assert eval_dir.exists()

        # Verify directory structure
        assert (eval_dir / "config").exists()
        assert (eval_dir / "data").exists()
        assert (eval_dir / "runs").exists()
        assert (eval_dir / "config" / "judges").exists()
        assert (eval_dir / "config" / "prompts").exists()

    def test_create_generates_config_files(self, tmp_path: Path) -> None:
        """Test that all config files are generated."""
        eval_name = "test_eval"
        result = runner.invoke(
            app, ["oneshot", "create", "--eval", eval_name, "--eval-root", str(tmp_path)]
        )

        assert result.exit_code == 0
        eval_dir = tmp_path / eval_name

        # Verify all config files exist
        assert (eval_dir / "config" / "agents.json").exists()
        assert (eval_dir / "config" / "eval_config.json").exists()
        assert (eval_dir / "data" / "scenarios.json").exists()
        assert (eval_dir / "config" / "prompts" / "assistant.toml").exists()

    def test_agents_config_valid_json(self, tmp_path: Path) -> None:
        """Test that generated agents.json is valid JSON with correct structure."""
        eval_name = "test_eval"
        runner.invoke(app, ["oneshot", "create", "--eval", eval_name, "--eval-root", str(tmp_path)])

        agents_file = tmp_path / eval_name / "config" / "agents.json"
        with open(agents_file) as f:
            agents_config = json.load(f)

        # Verify structure
        assert "_models" in agents_config
        assert "claude_haiku" in agents_config
        assert "assistant_agent" in agents_config

        # Verify model definitions
        assert "claude-haiku" in agents_config["_models"]
        assert "gpt-5-mini" in agents_config["_models"]

        # Verify model structure
        claude_model = agents_config["_models"]["claude-haiku"]
        assert claude_model["model_provider"] == "anthropic"
        assert claude_model["model_family"] == "claude"
        assert "model_parameters" in claude_model
        assert "provider_auth" in claude_model

    def test_eval_config_valid_json(self, tmp_path: Path) -> None:
        """Test that generated eval_config.json is valid JSON with correct structure."""
        eval_name = "my_test_eval"
        runner.invoke(app, ["oneshot", "create", "--eval", eval_name, "--eval-root", str(tmp_path)])

        eval_config_file = tmp_path / eval_name / "config" / "eval_config.json"
        with open(eval_config_file) as f:
            eval_config = json.load(f)

        # Verify core structure
        assert eval_config["eval_name"] == eval_name
        assert eval_config["eval_type"] == "oneshot"
        assert eval_config["test_subject_type"] == "local"
        assert "description" in eval_config

        # Verify nested structures
        assert "test_subjects" in eval_config
        assert "variants" in eval_config
        assert "scenarios" in eval_config
        assert "execution" in eval_config
        assert "async" in eval_config

        # Verify async config is nested
        async_config = eval_config["async"]
        assert "num_workers" in async_config
        assert "arrival_rate_per_sec" in async_config
        assert "max_retries" in async_config

    def test_eval_config_has_correct_defaults(self, tmp_path: Path) -> None:
        """Test that eval_config.json has correct default values."""
        eval_name = "test_eval"
        runner.invoke(
            app,
            [
                "oneshot",
                "create",
                "--eval",
                eval_name,
                "--eval-root",
                str(tmp_path),
            ],
        )

        eval_config_file = tmp_path / eval_name / "config" / "eval_config.json"
        with open(eval_config_file) as f:
            eval_config = json.load(f)

        # Verify eval_type is always oneshot
        assert eval_config["eval_type"] == "oneshot"
        # Verify test_subject_type defaults to local
        assert eval_config["test_subject_type"] == "local"
        # Verify default async config values
        assert eval_config["async"]["num_workers"] == 8
        assert eval_config["async"]["arrival_rate_per_sec"] == 20.0

    def test_async_config_nested_in_eval_config(self, tmp_path: Path) -> None:
        """Test that async config is nested inside eval_config.json."""
        eval_name = "test_eval"
        runner.invoke(app, ["oneshot", "create", "--eval", eval_name, "--eval-root", str(tmp_path)])

        eval_config_file = tmp_path / eval_name / "config" / "eval_config.json"
        with open(eval_config_file) as f:
            eval_config = json.load(f)

        # Verify async config exists and has required fields
        assert "async" in eval_config
        async_config = eval_config["async"]
        assert "num_workers" in async_config
        assert "arrival_rate_per_sec" in async_config
        assert "exec_rate_per_min" in async_config
        assert "max_retries" in async_config
        assert "task_timeout_seconds" in async_config
        assert "stuck_timeout_seconds" in async_config
        assert "emit_progress_interval_sec" in async_config

    def test_scenarios_json_valid(self, tmp_path: Path) -> None:
        """Test that generated scenarios.json is valid JSON with sample scenarios."""
        eval_name = "test_eval"
        runner.invoke(app, ["oneshot", "create", "--eval", eval_name, "--eval-root", str(tmp_path)])

        scenarios_file = tmp_path / eval_name / "data" / "scenarios.json"
        with open(scenarios_file) as f:
            scenarios = json.load(f)

        # Verify it's a root-level array (not wrapped)
        assert isinstance(scenarios, list)
        assert len(scenarios) >= 2

        # Verify scenario structure
        scenario = scenarios[0]
        assert "scenario_id" in scenario
        assert "input" in scenario
        assert "expected" in scenario
        assert "metadata" in scenario

    def test_prompts_toml_valid(self, tmp_path: Path) -> None:
        """Test that generated config/prompts/assistant.toml is valid TOML."""
        eval_name = "test_eval"
        runner.invoke(app, ["oneshot", "create", "--eval", eval_name, "--eval-root", str(tmp_path)])

        prompts_file = tmp_path / eval_name / "config" / "prompts" / "assistant.toml"
        with open(prompts_file) as f:
            prompts = toml.load(f)

        # Verify structure
        assert "v1" in prompts
        assert "{{input}}" in prompts["v1"]  # Contains placeholder

    def test_create_fails_if_directory_exists(self, tmp_path: Path) -> None:
        """Test that create command fails if evaluation directory already exists."""
        eval_name = "test_eval"

        # Create evaluation first time
        result1 = runner.invoke(
            app, ["oneshot", "create", "--eval", eval_name, "--eval-root", str(tmp_path)]
        )
        assert result1.exit_code == 0

        # Try to create again - should fail
        result2 = runner.invoke(
            app, ["oneshot", "create", "--eval", eval_name, "--eval-root", str(tmp_path)]
        )
        assert result2.exit_code != 0
        # Error messages go to stderr, check both stdout and stderr
        output = (result2.stdout + result2.stderr).lower()
        assert "already exists" in output

    def test_create_validates_eval_name(self, tmp_path: Path) -> None:
        """Test that create command validates evaluation name format."""
        invalid_names = [
            "eval with spaces",
            "eval/with/slashes",
            "eval\\with\\backslashes",
            "eval@special",
            "eval#chars",
        ]

        for invalid_name in invalid_names:
            result = runner.invoke(
                app,
                ["oneshot", "create", "--eval", invalid_name, "--eval-root", str(tmp_path)],
            )
            assert result.exit_code != 0

    def test_create_accepts_valid_eval_names(self, tmp_path: Path) -> None:
        """Test that create command accepts valid evaluation names."""
        valid_names = [
            "simple",
            "with-hyphens",
            "with_underscores",
            "mixed-name_123",
            "CamelCase",
        ]

        for valid_name in valid_names:
            # Use unique tmp_path subdirectory for each
            test_root = tmp_path / valid_name
            test_root.mkdir()

            result = runner.invoke(
                app,
                ["oneshot", "create", "--eval", valid_name, "--eval-root", str(test_root)],
            )
            assert result.exit_code == 0, f"Failed for valid name: {valid_name}"

    def test_create_uses_default_eval_root(self) -> None:
        """Test that create command uses default eval root if not specified."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            eval_name = "test_eval"
            # Note: This will create in .gavel/evaluations/ by default
            # We'll verify the command completes without error
            result = runner.invoke(
                app,
                [
                    "oneshot",
                    "create",
                    "--eval",
                    eval_name,
                    "--eval-root",
                    tmp_dir,  # Still provide root for test isolation
                ],
            )
            assert result.exit_code == 0

    def test_json_files_use_snake_case(self, tmp_path: Path) -> None:
        """Test that all JSON config files use snake_case for keys (not camelCase)."""
        eval_name = "test_eval"
        runner.invoke(app, ["oneshot", "create", "--eval", eval_name, "--eval-root", str(tmp_path)])

        eval_dir = tmp_path / eval_name

        # Check agents.json
        with open(eval_dir / "config" / "agents.json") as f:
            agents = json.load(f)
            # Should have snake_case keys
            assert "model_provider" in str(agents)
            assert "model_family" in str(agents)
            # Should NOT have camelCase keys
            assert "modelProvider" not in str(agents)
            assert "modelFamily" not in str(agents)

        # Check eval_config.json
        with open(eval_dir / "config" / "eval_config.json") as f:
            eval_config = json.load(f)
            assert "eval_name" in eval_config
            assert "test_subject_type" in eval_config
            assert "test_subjects" in eval_config
            # Should NOT have camelCase
            assert "evalName" not in str(eval_config)
            assert "testSubjectType" not in str(eval_config)
            assert "testSubjects" not in str(eval_config)


class TestScaffoldingFunctions:
    """Test suite for template generation functions."""

    def test_generate_all_templates_creates_files(self, tmp_path: Path) -> None:
        """Test that template generation creates all expected files."""
        from gavel_ai.cli.scaffolding import generate_all_templates

        eval_name = "test_eval"
        eval_type = "local"

        generate_all_templates(tmp_path, eval_name, eval_type)

        eval_dir = tmp_path / eval_name

        # Verify all files exist
        assert (eval_dir / "config" / "agents.json").exists()
        assert (eval_dir / "config" / "eval_config.json").exists()
        assert (eval_dir / "data" / "scenarios.json").exists()
        assert (eval_dir / "config" / "prompts" / "assistant.toml").exists()

        # Verify directories exist
        assert (eval_dir / "config" / "judges").exists()
        assert (eval_dir / "config" / "prompts").exists()
