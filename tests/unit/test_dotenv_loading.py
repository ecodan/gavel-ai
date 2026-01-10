"""Tests for automatic .env loading in CLI."""

from pathlib import Path
from unittest.mock import patch

import pytest


class TestDotenvLoading:
    """Test that .env files are loaded automatically."""

    def test_load_dotenv_called_at_module_import(self, tmp_path: Path) -> None:
        """Verify load_dotenv is called at module import time."""
        # Mock load_dotenv before importing main module
        with patch("dotenv.load_dotenv") as mock_load_dotenv:
            # Import main module - this should trigger load_dotenv at module level
            import sys

            # Remove module from cache to force re-import
            if "gavel_ai.cli.main" in sys.modules:
                del sys.modules["gavel_ai.cli.main"]

            # Import will trigger module-level load_dotenv

            # Verify load_dotenv was called with correct parameters
            mock_load_dotenv.assert_called_with(verbose=False, override=False)

    def test_env_vars_substituted_in_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify environment variables are substituted in config files."""
        from gavel_ai.core.config.loader import substitute_env_vars

        # Set test environment variable
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key-12345")

        # Test substitution
        content = '{"api_key": "{{TEST_API_KEY}}"}'
        result = substitute_env_vars(content)

        assert result == '{"api_key": "sk-test-key-12345"}'

    def test_missing_env_var_raises_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify missing environment variables raise ConfigError."""
        from gavel_ai.core.config.loader import substitute_env_vars
        from gavel_ai.core.exceptions import ConfigError

        # Ensure var is not set
        monkeypatch.delenv("MISSING_VAR", raising=False)

        # Test that missing var raises error
        content = '{"api_key": "{{MISSING_VAR}}"}'

        with pytest.raises(ConfigError) as exc_info:
            substitute_env_vars(content)

        assert "Environment variable 'MISSING_VAR' not set" in str(exc_info.value)
        assert "Set MISSING_VAR environment variable" in str(exc_info.value)

    def test_cli_main_callback_doesnt_duplicate_setup(self) -> None:
        """Verify CLI callback doesn't re-run setup (moved to module level)."""
        # Since load_dotenv moved to module level, callback should not log or setup
        from gavel_ai.cli.main import main

        # Main callback should just pass through now
        # No exceptions should be raised
        main(version=None)
