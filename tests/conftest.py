"""
Pytest configuration and shared fixtures for gavel-ai tests.

This module provides:
- Logging fixtures
- Mock provider fixtures
- Sample configuration fixtures
- Temporary directory fixtures
"""

import logging
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

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
                "name": "test_judge",
                "type": "deepeval.similarity",
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


@pytest.fixture
def mock_deepeval_metrics():
    """
    Mock all DeepEval metrics to avoid API key requirements in tests.

    Returns a dict of mocked metric instances that can be configured per test.
    """
    with (
        patch("gavel_ai.judges.deepeval_judge.AnswerRelevancyMetric") as mock_relevancy,
        patch("gavel_ai.judges.deepeval_judge.ContextualRelevancyMetric") as mock_contextual,
        patch("gavel_ai.judges.deepeval_judge.FaithfulnessMetric") as mock_faithfulness,
        patch("gavel_ai.judges.deepeval_judge.HallucinationMetric") as mock_hallucination,
        patch("gavel_ai.judges.deepeval_judge.GEval") as mock_geval,
    ):
        # Create mock instances that will be returned
        mock_relevancy_instance = MagicMock()
        mock_contextual_instance = MagicMock()
        mock_faithfulness_instance = MagicMock()
        mock_hallucination_instance = MagicMock()
        mock_geval_instance = MagicMock()

        # Configure the class mocks to return the instances
        mock_relevancy.return_value = mock_relevancy_instance
        mock_contextual.return_value = mock_contextual_instance
        mock_faithfulness.return_value = mock_faithfulness_instance
        mock_hallucination.return_value = mock_hallucination_instance
        mock_geval.return_value = mock_geval_instance

        # Import and patch the JUDGE_TYPE_MAP to use our mocks
        from gavel_ai.judges.deepeval_judge import DeepEvalJudge

        original_map = DeepEvalJudge.JUDGE_TYPE_MAP.copy()
        DeepEvalJudge.JUDGE_TYPE_MAP = {
            "deepeval.answer_relevancy": mock_relevancy,
            "deepeval.contextual_relevancy": mock_contextual,
            "deepeval.faithfulness": mock_faithfulness,
            "deepeval.hallucination": mock_hallucination,
            "deepeval.geval": mock_geval,
        }

        yield {
            "AnswerRelevancyMetric": mock_relevancy,
            "ContextualRelevancyMetric": mock_contextual,
            "FaithfulnessMetric": mock_faithfulness,
            "HallucinationMetric": mock_hallucination,
            "GEval": mock_geval,
            "relevancy_instance": mock_relevancy_instance,
            "contextual_instance": mock_contextual_instance,
            "faithfulness_instance": mock_faithfulness_instance,
            "hallucination_instance": mock_hallucination_instance,
            "geval_instance": mock_geval_instance,
        }

        # Restore original map
        DeepEvalJudge.JUDGE_TYPE_MAP = original_map


# Markers for test categorization
def pytest_configure(config: Any) -> None:
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "asyncio: Async tests")


# Telemetry test fixtures
@pytest.fixture(scope="session", autouse=True)
def ensure_telemetry_initialized():
    """
    Ensure telemetry module is properly initialized for all tests.

    This fixture runs once per session and ensures our DynamicSpanProcessor
    is properly connected to the global TracerProvider. This is needed because
    pytest plugins (deepeval, logfire) may initialize OT before our module.
    """
    from gavel_ai.telemetry import spans

    # Force re-registration of our processor if needed
    if spans._dynamic_processor is None:
        spans._tracer_provider = spans._initialize_tracer_provider()

    yield

    # Reset telemetry after all tests
    from gavel_ai.telemetry import reset_telemetry

    reset_telemetry()


@pytest.fixture
def reset_telemetry_after_test():
    """Reset telemetry state after each test that uses this fixture."""
    from gavel_ai.telemetry import reset_telemetry

    yield
    reset_telemetry()
