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


# Module-level logger instance (created on import)
logger = create_logger(LOGGER_NAME)

__all__ = ["create_logger", "logger", "LOGGER_NAME", "LOG_FORMAT", "LOG_DATE_FORMAT"]
