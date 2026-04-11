import pytest

pytestmark = pytest.mark.unit
"""
Unit tests for CLI common utilities and error handling.
"""

from unittest.mock import patch

import pytest
import typer

from gavel_ai.cli.common import handle_error
from gavel_ai.core.exceptions import GavelError


class TestHandleError:
    """Test error handling for CLI commands."""

    def test_handle_gavel_error_prints_formatted_message(self, capsys):
        """handle_error prints formatted message for GavelError."""
        error = GavelError("ConfigError: Invalid config file - Check config.json")

        with pytest.raises(typer.Exit) as exc_info:
            handle_error(error)

        # Check exit code
        assert exc_info.value.exit_code == 1

        # Check stderr output
        captured = capsys.readouterr()
        assert "Error: ConfigError: Invalid config file - Check config.json" in captured.err

    def test_handle_generic_error_prints_unexpected_message(self, capsys):
        """handle_error prints unexpected error message for generic exceptions."""
        error = ValueError("Something went wrong")

        with pytest.raises(typer.Exit) as exc_info:
            handle_error(error)

        # Check exit code
        assert exc_info.value.exit_code == 1

        # Check stderr output
        captured = capsys.readouterr()
        assert "Unexpected error: Something went wrong" in captured.err

    def test_handle_error_uses_red_color(self):
        """handle_error uses red color for error messages."""
        error = GavelError("Test error")

        with patch("typer.secho") as mock_secho:
            with pytest.raises(typer.Exit):
                handle_error(error)

            # Verify secho was called with red color
            mock_secho.assert_called_once()
            call_args = mock_secho.call_args
            assert call_args.kwargs["fg"] == typer.colors.RED
            assert call_args.kwargs["err"] is True

    def test_handle_error_always_exits_with_code_1(self):
        """handle_error always exits with code 1."""
        error = RuntimeError("Test")

        with pytest.raises(typer.Exit) as exc_info:
            handle_error(error)

        assert exc_info.value.exit_code == 1

    def test_handle_error_returns_noreturn_type(self):
        """handle_error has NoReturn type annotation."""
        from typing import get_type_hints

        hints = get_type_hints(handle_error)
        assert hints["return"].__name__ == "NoReturn"
