import pytest

pytestmark = pytest.mark.unit
"""
Tests for conversational generate command functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer

from gavel_ai.cli.commands.conv import create, generate
from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ProcessorError


class TestConversationalGenerateCommands:
    """Test conversational generate command functionality."""

    @pytest.fixture
    def mock_run_context(self):
        """Create a mock RunContext for testing."""
        context = MagicMock(spec=RunContext)
        context.eval_context = MagicMock()
        context.run_logger = MagicMock()
        context.run_id = "test-run"
        return context

    @pytest.fixture
    def temp_eval_dir(self):
        """Create a temporary evaluation directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_create_command_exists(self):
        """Test that create command is properly registered (AC: 1)."""
        assert callable(create)
        assert callable(create)

    def test_create_scaffolding_placeholder(self):
        """Test that create command echoes current status."""
        with patch("typer.echo") as mock_echo:
            create(eval_name="test_eval")
            mock_echo.assert_any_call(
                "Creating conversational evaluation scaffold for 'test_eval'..."
            )

    def test_generate_command_executes_step(self, mock_run_context):
        """Test that generate command instantiates and executes GenerateStep (AC: 1, 2)."""
        with patch("gavel_ai.cli.commands.conv.LocalFileSystemEvalContext"):
            with patch("gavel_ai.cli.commands.conv.LocalRunContext") as mock_run_ctx_cls:
                mock_run_ctx_cls.return_value = mock_run_context

                with patch("gavel_ai.cli.commands.conv.GenerateStep") as mock_step_cls:
                    mock_step_inst = mock_step_cls.return_value
                    mock_step_inst.execute = AsyncMock(return_value=None)

                    # Execute generate command
                    generate(eval_name="test_eval")

                    # Verify GenerateStep execution
                    mock_step_cls.assert_called_once()
                    mock_step_inst.execute.assert_called_once_with(mock_run_context)

    def test_generate_command_handles_errors(self, mock_run_context):
        """Test that generate command handles ProcessorError correctly (AC: 5)."""
        with patch("gavel_ai.cli.commands.conv.LocalFileSystemEvalContext"):
            with patch("gavel_ai.cli.commands.conv.LocalRunContext") as mock_run_ctx_cls:
                mock_run_ctx_cls.return_value = mock_run_context

                with patch("gavel_ai.cli.commands.conv.GenerateStep") as mock_step_cls:
                    mock_step_inst = mock_step_cls.return_value
                    mock_step_inst.execute = AsyncMock(
                        side_effect=ProcessorError("Generation failed")
                    )

                    with patch("typer.secho") as mock_secho:
                        with pytest.raises(typer.Exit) as excinfo:
                            generate(eval_name="test_eval")

                        assert excinfo.value.exit_code == 1
                        mock_secho.assert_any_call(
                            "Execution Error: Generation failed", fg=typer.colors.RED, err=True
                        )

    def test_generate_command_supports_custom_prompt(self, mock_run_context, temp_eval_dir):
        """Test support for --prompt-file flag (AC: 4)."""
        prompt_path = temp_eval_dir / "custom.toml"
        prompt_path.touch()

        with patch("gavel_ai.cli.commands.conv.LocalFileSystemEvalContext") as mock_eval_ctx_cls:
            mock_eval_ctx = mock_eval_ctx_cls.return_value
            mock_eval_ctx.eval_config.read.return_value = {}

            with patch("gavel_ai.cli.commands.conv.LocalRunContext") as mock_run_ctx_cls:
                mock_run_ctx_cls.return_value = mock_run_context

                with patch("gavel_ai.cli.commands.conv.GenerateStep") as mock_step_cls:
                    mock_step_inst = mock_step_cls.return_value
                    mock_step_inst.execute = AsyncMock(return_value=None)

                    generate(eval_name="test_eval", prompt_file=prompt_path)

                    # Check that config was updated with absolute path
                    mock_eval_ctx.eval_config.write.assert_called_once()
                    written_config = mock_eval_ctx.eval_config.write.call_args[0][0]
                    assert written_config["scenario_generation"]["prompt_file"] == str(
                        prompt_path.absolute()
                    )
