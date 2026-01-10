"""
Centralized logging configuration for gavel-ai.

This module provides a single logger instance with standard formatting
that all modules in gavel-ai should use for consistent log output.

Standard format: "%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"

Example:
    ```python
    from gavel_ai.log_config import create_logger

    logger = create_logger(__name__)
    logger.info("Application started")
    ```
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# Module-level logger name constant
LOGGER_NAME = "gavel-ai"

# Standard log format used throughout the project
LOG_FORMAT = "%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Determine debug mode from environment
DEBUG_MODE = os.getenv("GAVEL_DEBUG", "false").lower() in ("true", "1", "yes")


def create_logger(
    name: str = LOGGER_NAME,
    level: Optional[int] = None,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Create and configure a logger for the gavel-ai application.

    Args:
        name: Logger name (default: LOGGER_NAME = "gavel-ai")
        level: Log level (default: DEBUG if GAVEL_DEBUG=true, else INFO)
        log_file: Optional path to log file for file-based logging

    Returns:
        Configured logger instance

    Example:
        ```python
        logger = create_logger(__name__)
        logger.info("Starting process")

        # Or with explicit file logging
        logger = create_logger(__name__, log_file="app.log")
        ```
    """
    # Get logger instance
    logger = logging.getLogger(name)

    # Only configure if not already configured (avoid duplicate handlers)
    if logger.handlers:
        return logger

    # Set log level
    if level is None:
        level = logging.DEBUG if DEBUG_MODE else logging.INFO
    logger.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Add stdout handler (always enabled for development/debugging)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(level)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    # Add file handler if requested
    if log_file:
        try:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except (OSError, IOError) as e:
            logger.warning(f"Could not create file logger at {log_file}: {e}")

    return logger


def get_application_logger(
    base_dir: str = ".gavel",
    level: Optional[int] = None,
) -> logging.Logger:
    """
    Get application-level logger with file and console handlers.

    Creates a logger that writes to {base_dir}/gavel.log with automatic
    log rotation (10MB max, 5 backups) and console output. Use for top-level
    lifecycle events like application startup, eval creation, and shutdown.

    Args:
        base_dir: Base directory for logs (default: .gavel)
        level: Log level (default: read from LOG_LEVEL_APP env var, or INFO)

    Returns:
        Configured application logger

    Example:
        ```python
        from gavel_ai.log_config import get_application_logger

        app_logger = get_application_logger()
        app_logger.info("Gavel-AI v0.1.0 started")
        app_logger.info("Evaluation 'test_os' created")
        ```
    """
    # Create .gavel directory if doesn't exist
    log_dir = Path(base_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Application log file
    log_file = log_dir / "gavel.log"

    # Make logger name unique per base_dir to avoid handler conflicts
    # In production, base_dir is always ".gavel" so logger is reused
    # In tests, each tmp_path gets its own logger
    resolved_path = str(log_dir.resolve())
    # Use hash to keep name short but unique
    import hashlib

    path_hash = hashlib.md5(resolved_path.encode()).hexdigest()[:8]
    app_logger_name = f"{LOGGER_NAME}.app.{path_hash}"

    # Get logger instance
    logger = logging.getLogger(app_logger_name)

    # Only configure if not already configured (avoid duplicate handlers)
    if logger.handlers:
        return logger

    # Determine log level from environment (LOG_LEVEL_APP) or parameter
    if level is None:
        level_str = os.getenv("LOG_LEVEL_APP", "INFO").upper()
        try:
            level = getattr(logging, level_str)
        except AttributeError:
            level = logging.INFO
    logger.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Add stdout handler (console output)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(level)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    # Add file handler (with rotation)
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (OSError, IOError) as e:
        logger.warning(f"Could not create file logger at {log_file}: {e}")

    # Disable propagation to prevent duplicate logs from parent loggers
    logger.propagate = False

    return logger


def get_run_logger(
    run_id: str,
    eval_name: str,
    base_dir: str = ".gavel",
    level: Optional[int] = None,
) -> logging.Logger:
    """
    Get run-specific logger with file and console handlers.

    Creates a logger that writes to
    {base_dir}/evaluations/{eval_name}/runs/{run_id}/run.log and console.
    Use for run-specific operations like config loading, scenario execution,
    and judge results.

    Args:
        run_id: Run identifier (e.g., "run-20251231-120000")
        eval_name: Evaluation name (e.g., "test_os")
        base_dir: Base directory for logs (default: .gavel)
        level: Log level (default: read from LOG_LEVEL_RUN env var, or INFO)

    Returns:
        Configured run-specific logger

    Example:
        ```python
        from gavel_ai.log_config import get_run_logger

        run_logger = get_run_logger(run_id="run-123", eval_name="test_os")
        run_logger.info("Loaded 15 scenarios")
        run_logger.info("Executing scenario 'test-1'")
        ```
    """
    # Create run log directory
    run_dir = Path(base_dir) / "evaluations" / eval_name / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Run log file (no rotation)
    log_file = run_dir / "run.log"

    # Create logger with unique name
    logger_name = f"{LOGGER_NAME}.run.{run_id}"

    # Get logger instance
    logger = logging.getLogger(logger_name)

    # Only configure if not already configured (avoid duplicate handlers)
    if logger.handlers:
        return logger

    # Determine log level from environment (LOG_LEVEL_RUN) or parameter
    if level is None:
        level_str = os.getenv("LOG_LEVEL_RUN", "INFO").upper()
        try:
            level = getattr(logging, level_str)
        except AttributeError:
            level = logging.INFO
    logger.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Add stdout handler (console output)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(level)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    # Add file handler (no rotation for run logs - single file per run)
    try:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (OSError, IOError) as e:
        # Fallback: log to application logger if run logger fails
        app_logger = get_application_logger(base_dir)
        app_logger.warning(f"Could not create run logger at {log_file}: {e}")

    # Disable propagation to prevent duplicate logs from parent loggers
    logger.propagate = False

    return logger


# Module-level logger instance (created on import)
logger = create_logger(LOGGER_NAME)

__all__ = [
    "create_logger",
    "get_application_logger",
    "get_run_logger",
    "logger",
    "LOGGER_NAME",
    "LOG_FORMAT",
    "LOG_DATE_FORMAT",
]
