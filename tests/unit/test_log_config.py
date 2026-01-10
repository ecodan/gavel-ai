"""
Unit tests for gavel_ai.log_config module.

Tests two-level logging architecture:
- Application-level logger (rolling file handler)
- Run-level logger (single file per run)
"""

import logging
from pathlib import Path

import pytest

from gavel_ai.log_config import (
    LOG_FORMAT,
    LOGGER_NAME,
    create_logger,
    get_application_logger,
    get_run_logger,
)


@pytest.fixture(autouse=True)
def cleanup_loggers():
    """Clean up logger state after each test to prevent state pollution."""
    yield
    # After test completes, clean up all loggers created during the test
    # This prevents handler conflicts and state pollution between tests
    loggers_to_cleanup = []
    for logger_name in logging.Logger.manager.loggerDict:
        if logger_name.startswith(LOGGER_NAME):
            loggers_to_cleanup.append(logger_name)

    for logger_name in loggers_to_cleanup:
        logger = logging.getLogger(logger_name)
        # Remove all handlers
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        # Remove logger from manager
        if logger_name in logging.Logger.manager.loggerDict:
            del logging.Logger.manager.loggerDict[logger_name]


class TestCreateLogger:
    """Tests for existing create_logger function."""

    def test_create_logger_basic(self, tmp_path):
        """create_logger creates logger with stdout handler."""
        logger = create_logger(name="test-logger")

        assert logger is not None
        assert logger.name == "test-logger"
        assert len(logger.handlers) > 0

    def test_create_logger_with_file(self, tmp_path):
        """create_logger creates logger with file handler when log_file provided."""
        log_file = tmp_path / "test.log"

        logger = create_logger(name="test-logger-file", log_file=str(log_file))
        logger.info("Test message")

        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content
        assert "[INFO]" in content

    def test_create_logger_idempotent(self):
        """create_logger returns same logger on repeated calls (no duplicate handlers)."""
        logger1 = create_logger(name="test-idempotent")
        handler_count_1 = len(logger1.handlers)

        logger2 = create_logger(name="test-idempotent")
        handler_count_2 = len(logger2.handlers)

        assert logger1 is logger2
        assert handler_count_1 == handler_count_2  # No duplicate handlers


class TestGetApplicationLogger:
    """Tests for get_application_logger function."""

    def test_get_application_logger_creates_file(self, tmp_path):
        """Application logger creates .gavel/gavel.log with rotating handler."""
        logger = get_application_logger(base_dir=str(tmp_path))
        logger.info("Test application message")

        log_file = tmp_path / "gavel.log"
        assert log_file.exists()

        content = log_file.read_text()
        assert "Test application message" in content
        assert "[INFO]" in content

    def test_get_application_logger_creates_directory(self, tmp_path):
        """.gavel directory is created if it doesn't exist."""
        gavel_dir = tmp_path / ".gavel"
        assert not gavel_dir.exists()

        logger = get_application_logger(base_dir=str(tmp_path / ".gavel"))
        logger.info("Creating directory test")

        # Flush handlers to ensure file is written
        for handler in logger.handlers:
            handler.flush()

        assert gavel_dir.exists()
        assert (gavel_dir / "gavel.log").exists()

    def test_get_application_logger_format_compliance(self, tmp_path):
        """Application logger follows standard LOG_FORMAT."""
        logger = get_application_logger(base_dir=str(tmp_path))
        logger.info("Format test message")

        # Flush handlers to ensure file is written
        for handler in logger.handlers:
            handler.flush()

        log_file = tmp_path / "gavel.log"
        content = log_file.read_text()

        # Format: %(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s
        assert "[INFO]" in content
        assert "<test_log_config.py:" in content  # Filename with line number
        assert "Format test message" in content

    def test_get_application_logger_uses_correct_name(self, tmp_path):
        """Application logger uses LOGGER_NAME as base (child logger)."""
        logger = get_application_logger(base_dir=str(tmp_path))

        # Application logger is a child of LOGGER_NAME (gavel-ai.app.<hash>)
        assert logger.name.startswith(LOGGER_NAME)
        assert ".app." in logger.name  # Includes path hash for uniqueness

    def test_get_application_logger_rotation_handler(self, tmp_path):
        """Application logger uses RotatingFileHandler for log rotation."""
        from logging.handlers import RotatingFileHandler

        logger = get_application_logger(base_dir=str(tmp_path))

        # Find RotatingFileHandler in handlers
        rotating_handlers = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]

        assert len(rotating_handlers) > 0
        handler = rotating_handlers[0]
        assert handler.maxBytes == 10 * 1024 * 1024  # 10MB
        assert handler.backupCount == 5

    def test_get_application_logger_rotation_behavior(self, tmp_path):
        """Application logger rotates files when 10MB limit reached."""
        logger = get_application_logger(base_dir=str(tmp_path))

        # Write >10MB of logs to trigger rotation
        # Each log line is ~1KB, so 11000 lines = ~11MB
        for i in range(11000):
            logger.info("x" * 1000)

        # Flush handlers to ensure file is written
        for handler in logger.handlers:
            handler.flush()

        # Check that rotation occurred
        assert (tmp_path / "gavel.log").exists()
        # Rotation creates gavel.log.1 when limit exceeded
        assert (tmp_path / "gavel.log.1").exists()


class TestGetRunLogger:
    """Tests for get_run_logger function."""

    def test_get_run_logger_creates_file(self, tmp_path):
        """Run logger creates run-specific log file."""
        logger = get_run_logger(
            run_id="run-test-123",
            eval_name="test_eval",
            base_dir=str(tmp_path),
        )
        logger.info("Run message")

        log_file = tmp_path / "evaluations" / "test_eval" / "runs" / "run-test-123" / "run.log"
        assert log_file.exists()

        content = log_file.read_text()
        assert "Run message" in content

    def test_get_run_logger_creates_directory_structure(self, tmp_path):
        """Run logger creates complete directory structure if missing."""
        run_dir = tmp_path / "evaluations" / "test_eval" / "runs" / "run-test-456"
        assert not run_dir.exists()

        logger = get_run_logger(
            run_id="run-test-456",
            eval_name="test_eval",
            base_dir=str(tmp_path),
        )
        logger.info("Directory creation test")

        assert run_dir.exists()
        assert (run_dir / "run.log").exists()

    def test_get_run_logger_unique_names(self, tmp_path):
        """Each run logger has unique name based on run_id."""
        logger1 = get_run_logger(
            run_id="run-001",
            eval_name="test",
            base_dir=str(tmp_path),
        )
        logger2 = get_run_logger(
            run_id="run-002",
            eval_name="test",
            base_dir=str(tmp_path),
        )

        assert logger1.name == f"{LOGGER_NAME}.run.run-001"
        assert logger2.name == f"{LOGGER_NAME}.run.run-002"
        assert logger1 is not logger2

    def test_get_run_logger_no_rotation(self, tmp_path):
        """Run logger uses FileHandler (no rotation) instead of RotatingFileHandler."""
        from logging.handlers import RotatingFileHandler

        logger = get_run_logger(
            run_id="run-test-789",
            eval_name="test_eval",
            base_dir=str(tmp_path),
        )

        # Should NOT have RotatingFileHandler
        rotating_handlers = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]
        assert len(rotating_handlers) == 0

        # Should have regular FileHandler
        file_handlers = [
            h
            for h in logger.handlers
            if isinstance(h, logging.FileHandler) and not isinstance(h, RotatingFileHandler)
        ]
        assert len(file_handlers) > 0

    def test_get_run_logger_format_compliance(self, tmp_path):
        """Run logger follows standard LOG_FORMAT."""
        logger = get_run_logger(
            run_id="run-format-test",
            eval_name="test_eval",
            base_dir=str(tmp_path),
        )
        logger.info("Format compliance test")

        log_file = tmp_path / "evaluations" / "test_eval" / "runs" / "run-format-test" / "run.log"
        content = log_file.read_text()

        # Format: %(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s
        assert "[INFO]" in content
        assert "<test_log_config.py:" in content
        assert "Format compliance test" in content

    def test_get_run_logger_error_with_traceback(self, tmp_path):
        """Run logger logs errors with stack traces when exc_info=True."""
        logger = get_run_logger(
            run_id="run-error-test",
            eval_name="test_eval",
            base_dir=str(tmp_path),
        )

        try:
            raise ValueError("Test error for traceback")
        except ValueError:
            logger.error("Error occurred", exc_info=True)

        log_file = tmp_path / "evaluations" / "test_eval" / "runs" / "run-error-test" / "run.log"
        content = log_file.read_text()

        assert "[ERROR]" in content
        assert "Error occurred" in content
        assert "Traceback" in content
        assert "ValueError: Test error for traceback" in content

    def test_get_run_logger_idempotent(self, tmp_path):
        """get_run_logger returns same logger for same run_id (no duplicate handlers)."""
        logger1 = get_run_logger(
            run_id="run-idempotent",
            eval_name="test_eval",
            base_dir=str(tmp_path),
        )
        handler_count_1 = len(logger1.handlers)

        logger2 = get_run_logger(
            run_id="run-idempotent",
            eval_name="test_eval",
            base_dir=str(tmp_path),
        )
        handler_count_2 = len(logger2.handlers)

        assert logger1 is logger2
        assert handler_count_1 == handler_count_2  # No duplicate handlers


class TestMultipleLoggers:
    """Tests for interactions between application and run loggers."""

    def test_application_and_run_loggers_independent(self, tmp_path):
        """Application and run loggers write to separate files."""
        app_logger = get_application_logger(base_dir=str(tmp_path))
        run_logger = get_run_logger(
            run_id="run-test",
            eval_name="test_eval",
            base_dir=str(tmp_path),
        )

        app_logger.info("Application message")
        run_logger.info("Run message")

        # Check application log
        app_log = tmp_path / "gavel.log"
        assert app_log.exists()
        app_content = app_log.read_text()
        assert "Application message" in app_content
        assert "Run message" not in app_content  # Should not leak

        # Check run log
        run_log = tmp_path / "evaluations" / "test_eval" / "runs" / "run-test" / "run.log"
        assert run_log.exists()
        run_content = run_log.read_text()
        assert "Run message" in run_content
        assert "Application message" not in run_content  # Should not leak

    def test_multiple_run_loggers_same_eval(self, tmp_path):
        """Multiple runs for same eval create separate log files."""
        logger1 = get_run_logger(
            run_id="run-001",
            eval_name="test_eval",
            base_dir=str(tmp_path),
        )
        logger2 = get_run_logger(
            run_id="run-002",
            eval_name="test_eval",
            base_dir=str(tmp_path),
        )

        logger1.info("Run 001 message")
        logger2.info("Run 002 message")

        # Flush handlers to ensure files are written
        for handler in logger1.handlers:
            handler.flush()
        for handler in logger2.handlers:
            handler.flush()

        log1 = tmp_path / "evaluations" / "test_eval" / "runs" / "run-001" / "run.log"
        log2 = tmp_path / "evaluations" / "test_eval" / "runs" / "run-002" / "run.log"

        assert log1.exists()
        assert log2.exists()

        content1 = log1.read_text()
        content2 = log2.read_text()

        assert "Run 001 message" in content1
        assert "Run 002 message" not in content1

        assert "Run 002 message" in content2
        assert "Run 001 message" not in content2
