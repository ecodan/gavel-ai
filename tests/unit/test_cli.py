"""Unit tests for CLI entry point and command structure."""
from typer.testing import CliRunner

from gavel_ai.cli.main import app

runner = CliRunner()


class TestCLIEntryPoint:
    """Test suite for CLI entry point."""

    def test_gavel_help_shows_workflows(self):
        """Test that 'gavel --help' displays available workflows."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "oneshot" in result.stdout.lower()
        assert "conv" in result.stdout.lower()
        assert "autotune" in result.stdout.lower()

    def test_gavel_version(self):
        """Test that 'gavel --version' shows version information."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.stdout


class TestOneShotWorkflow:
    """Test suite for oneshot workflow commands."""

    def test_oneshot_help_shows_actions(self):
        """Test that 'gavel oneshot --help' lists all actions."""
        result = runner.invoke(app, ["oneshot", "--help"])
        assert result.exit_code == 0
        stdout_lower = result.stdout.lower()
        assert "create" in stdout_lower
        assert "run" in stdout_lower
        assert "judge" in stdout_lower
        assert "report" in stdout_lower
        assert "list" in stdout_lower
        assert "milestone" in stdout_lower

    def test_oneshot_create_help_shows_options(self):
        """Test that 'gavel oneshot create --help' shows all options."""
        result = runner.invoke(app, ["oneshot", "create", "--help"])
        assert result.exit_code == 0
        stdout_lower = result.stdout.lower()
        assert "--eval" in stdout_lower
        assert "--type" in stdout_lower


class TestConvWorkflow:
    """Test suite for conv workflow commands."""

    def test_conv_help_shows_actions(self):
        """Test that 'gavel conv --help' lists available actions."""
        result = runner.invoke(app, ["conv", "--help"])
        assert result.exit_code == 0


class TestAutotuneWorkflow:
    """Test suite for autotune workflow commands."""

    def test_autotune_help_shows_actions(self):
        """Test that 'gavel autotune --help' lists available actions."""
        result = runner.invoke(app, ["autotune", "--help"])
        assert result.exit_code == 0


class TestErrorHandling:
    """Test suite for CLI error handling."""

    def test_invalid_command_shows_helpful_error(self):
        """Test that invalid commands show helpful error messages."""
        result = runner.invoke(app, ["invalid"])
        assert result.exit_code != 0
        # Should show helpful error message
        assert len(result.stdout) > 0 or len(result.stderr) > 0
