"""
Pytest configuration and shared fixtures for gavel-ai tests.

This module provides:
- Logging fixtures
- Mock provider fixtures
- Sample configuration fixtures
- Temporary directory fixtures
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest


@pytest.fixture
def temp_eval_dir() -> Path:
    """Create and return a temporary evaluation directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_config_file(temp_eval_dir: Path) -> Path:
    """Create and return a temporary config file path."""
    config_file = temp_eval_dir / "config.json"
    return config_file


@pytest.fixture
def sample_processor_config() -> Dict[str, Any]:
    """Return sample processor configuration."""
    return {
        "processor_type": "prompt_input",
        "parallelism": 1,
        "timeout_seconds": 30,
        "metadata": {"version": "1.0"},
    }


@pytest.fixture
def sample_eval_config() -> Dict[str, Any]:
    """Return sample evaluation configuration."""
    return {
        "eval_name": "test_eval",
        "workflow_type": "oneshot",
        "processor_config": {
            "processor_type": "prompt_input",
            "parallelism": 1,
        },
        "judge_config": [
            {
                "judge_id": "test_judge",
                "judge_type": "deepeval.similarity",
            }
        ],
    }


@pytest.fixture
def sample_scenarios() -> list:
    """Return sample test scenarios."""
    return [
        {
            "id": "scenario_1",
            "description": "Test scenario 1",
            "variants": [
                {
                    "id": "variant_1",
                    "name": "Test variant",
                    "input": "Test input",
                    "expected": "Test output",
                }
            ],
        },
        {
            "id": "scenario_2",
            "description": "Test scenario 2",
            "variants": [
                {
                    "id": "variant_1",
                    "name": "Another variant",
                    "input": "Another input",
                    "expected": "Another output",
                }
            ],
        },
    ]


@pytest.fixture
def mock_logger() -> logging.Logger:
    """Return a mock logger for testing."""
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)

    # Create a handler that logs to console for debugging
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)

    # Use standard format matching project conventions
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    if not logger.handlers:
        logger.addHandler(handler)

    return logger


@pytest.fixture(scope="session", autouse=True)
def setup_logging() -> None:
    """Configure logging for all tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# Mock provider fixtures (placeholders for future implementation)
@pytest.fixture
def mock_claude_provider() -> Dict[str, Any]:
    """Mock Claude provider configuration."""
    return {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "mock-key",
    }


@pytest.fixture
def mock_gpt_provider() -> Dict[str, Any]:
    """Mock GPT provider configuration."""
    return {
        "provider": "openai",
        "model": "gpt-4",
        "api_key": "mock-key",
    }


@pytest.fixture
def mock_ollama_provider() -> Dict[str, Any]:
    """Mock Ollama provider configuration."""
    return {
        "provider": "ollama",
        "model": "llama2",
        "base_url": "http://localhost:11434",
    }


# Markers for test categorization
def pytest_configure(config: Any) -> None:
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "asyncio: Async tests")
