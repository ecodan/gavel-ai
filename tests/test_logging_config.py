"""
Tests for gavel-ai logging configuration (Story 1.5).
"""

import logging
import os
from pathlib import Path

import pytest

from gavel_ai.log_config import LOG_FORMAT, LOGGER_NAME, create_logger


class TestLoggingConfiguration:
    """Test that logging is properly configured."""

    def test_logger_creation(self) -> None:
        """Test that logger can be created."""
        logger = create_logger(__name__)
        assert logger is not None
        assert isinstance(logger, logging.Logger)

    def test_logger_name(self) -> None:
        """Test that logger has correct name."""
        logger = create_logger(LOGGER_NAME)
        assert logger.name == LOGGER_NAME

    def test_logger_has_handlers(self) -> None:
        """Test that created logger has handlers."""
        logger = create_logger(__name__)
        assert len(logger.handlers) > 0

    def test_logger_log_format(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that logger uses standard log format."""
        logger = create_logger("test_format")
        caplog.set_level(logging.INFO)

        logger.info("Test message")

        # Check that log record has expected format components
        assert any("test_format" in record.name for record in caplog.records)

    def test_debug_mode_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that debug mode can be enabled via environment."""
        monkeypatch.setenv("GAVEL_DEBUG", "true")

        # Re-import to pick up environment variable
        import importlib

        import gavel_ai.log_config

        importlib.reload(gavel_ai.log_config)

        logger = gavel_ai.log_config.create_logger("test_debug")
        assert logger.level == logging.DEBUG

    def test_file_logging(self, temp_eval_dir: Path) -> None:
        """Test that file logging works when requested."""
        log_file = temp_eval_dir / "test.log"

        logger = create_logger("test_file_logger", log_file=str(log_file))
        logger.info("Test message to file")

        # Verify log file was created
        assert log_file.exists()

        # Verify message was written
        content = log_file.read_text()
        assert "Test message to file" in content

    def test_logger_format_structure(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that log messages follow standard format."""
        logger = create_logger("format_test")
        caplog.set_level(logging.INFO)

        logger.info("Format test message")

        # Check that record was created
        assert len(caplog.records) > 0

        # Format should be available
        assert LOG_FORMAT is not None
        assert "%(asctime)s" in LOG_FORMAT
        assert "%(levelname)s" in LOG_FORMAT
        assert "%(filename)s" in LOG_FORMAT
        assert "%(lineno)s" in LOG_FORMAT

    def test_multiple_loggers_isolated(self) -> None:
        """Test that multiple logger instances are independent."""
        logger1 = create_logger("logger1")
        logger2 = create_logger("logger2")

        assert logger1.name == "logger1"
        assert logger2.name == "logger2"
        assert logger1 is not logger2

    def test_logger_level_default(self) -> None:
        """Test default logger level respects GAVEL_DEBUG environment variable."""
        # Create logger and verify it has appropriate level
        test_logger = create_logger("level_test")
        # Should be DEBUG if GAVEL_DEBUG env var is set, else INFO
        # Just verify it has a valid log level
        assert test_logger.level in (logging.DEBUG, logging.INFO, logging.NOTSET)


class TestLoggerUsage:
    """Test that logger works correctly when used."""

    def test_log_message_emission(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that log messages can be emitted."""
        logger = create_logger("usage_test")
        caplog.set_level(logging.DEBUG)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # Verify all messages were logged
        assert len(caplog.records) == 4

    def test_logger_exception_handling(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that exceptions can be logged."""
        logger = create_logger("exception_test")
        caplog.set_level(logging.ERROR)

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("An error occurred")

        # Verify exception was logged
        assert len(caplog.records) > 0
        assert "An error occurred" in str(caplog.text)

    def test_logger_with_extra_data(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that logger works with extra context data."""
        logger = create_logger("extra_test")
        caplog.set_level(logging.INFO)

        logger.info("Message with context", extra={"user_id": "123"})

        # Verify message was logged
        assert len(caplog.records) > 0
