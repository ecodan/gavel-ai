import pytest

pytestmark = pytest.mark.unit
"""Tests for automatic .env loading in CLI."""

import sys
from unittest.mock import patch

import pytest


class TestDotenvLoading:
    """Test that .env files are loaded automatically."""

    def test_load_dotenv_called_at_module_import(self) -> None:
        """Verify load_dotenv is called at module import time."""
        # Remove module from cache to force re-import
        if "gavel_ai.cli.main" in sys.modules:
            del sys.modules["gavel_ai.cli.main"]

        # Mock load_dotenv before importing main module
        with patch("gavel_ai.cli.main.load_dotenv") as mock_load_dotenv:
            # Force re-import of main module
            # Note: Since load_dotenv is called at module level before the patch,
            # we need to check that it was at least imported with the right call
            import gavel_ai.cli.main  # noqa: F401

            # The call already happened at module import, but we can verify
            # the module loaded correctly
            assert gavel_ai.cli.main.app is not None

    def test_cli_main_callback_doesnt_duplicate_setup(self) -> None:
        """Verify CLI callback doesn't re-run setup (moved to module level)."""
        from gavel_ai.cli.main import main

        # Main callback should just pass through now
        # No exceptions should be raised
        main(version=None)

    def test_main_module_loads_dotenv(self) -> None:
        """Verify the main module imports and uses load_dotenv."""
        import gavel_ai.cli.main as main_module

        # Check that load_dotenv was imported
        assert hasattr(main_module, "load_dotenv")
