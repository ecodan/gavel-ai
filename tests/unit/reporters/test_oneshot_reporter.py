import pytest

pytestmark = pytest.mark.unit
"""
Tests for OneShotReporter using Unified Reporting Format.
"""

from datetime import datetime
from typing import Any, Dict, List

import pytest
from gavel_ai.models.runtime import ReporterConfig


class MockRun:
    """Mock Run instance with OneShot evaluation data."""

    def __init__(
        self,
        run_id: str = "run-20251230-120000",
        eval_name: str = "Claude vs GPT Comparison",
        results: List[Dict[str, Any]] = None,
    ):
        self.run_id = run_id
        self.metadata = {
            "eval_name": eval_name,
            "timestamp": "2025-12-30T12:00:00Z",
            "config_hash": "abc123",
            "scenario_count": 2,
            "variant_count": 2,
            "eval_type": "oneshot",
        }
        self.results = (
            results
            if results is not None
            else [
                {
                    "scenario_id": "scenario-1",
                    "variant_id": "claude",
                    "processor_output": "Paris is the capital of France.",
                    "scenario_input": "What is the capital of France?",
                    "judges": [
                        {
                            "judge_id": "similarity",
                            "score": 9,
                            "reasoning": "Accurate and concise.",
                            "evidence": "Direct answer to question",
                        }
                    ],
                    "timing_ms": 1500,
                    "timestamp": "2025-12-30T12:00:05Z"
                },
                {
                    "scenario_id": "scenario-1",
                    "variant_id": "gpt",
                    "processor_output": "The capital of France is Paris.",
                    "scenario_input": "What is the capital of France?",
                    "judges": [
                        {
                            "judge_id": "similarity",
                            "score": 8,
                            "reasoning": "Accurate but slightly wordy.",
                            "evidence": None,
                        }
                    ],
                    "timing_ms": 1200,
                    "timestamp": "2025-12-30T12:00:06Z"
                },
            ]
        )


@pytest.fixture
def mock_oneshot_run():
    """Mock Run with OneShot evaluation data."""
    return MockRun()


@pytest.fixture
def reporter_config():
    """ReporterConfig for testing."""
    return ReporterConfig(template_path="src/gavel_ai/reporters/templates", output_format="html")


@pytest.mark.asyncio
async def test_oneshot_reporter_generates_unified_html(mock_oneshot_run, reporter_config):
    """OneShotReporter generates complete HTML report in Unified Format."""
    from gavel_ai.reporters.oneshot_reporter import OneShotReporter

    reporter = OneShotReporter(reporter_config)
    output = await reporter.generate(mock_oneshot_run, "oneshot.html")

    # Verify Unified Spec elements
    assert "Claude vs GPT Comparison" in output
    assert "Run ID:" in output
    assert "Evaluation Summary" in output
    assert "Performance Summary" in output
    assert "Detailed Analysis" in output
    assert "comparison-grid" in output
    assert "turn-user" in output
    assert "turn-assistant" in output


@pytest.mark.asyncio
async def test_oneshot_reporter_mapping_to_turns(mock_oneshot_run, reporter_config):
    """Verify OneShot mapping: Input -> USER, Output -> ASSISTANT."""
    from gavel_ai.reporters.oneshot_reporter import OneShotReporter

    reporter = OneShotReporter(reporter_config)
    context = reporter._build_context(mock_oneshot_run)

    # Check first scenario
    scenarios = context["scenarios"]
    assert len(scenarios) == 1
    scenario = scenarios[0]
    
    variant = scenario["variants"]["claude"]
    assert len(variant["turns"]) == 2
    assert variant["turns"][0]["role"] == "user"
    assert variant["turns"][0]["content"] == "What is the capital of France?"
    assert variant["turns"][1]["role"] == "assistant"
    assert variant["turns"][1]["content"] == "Paris is the capital of France."
    assert variant["turns"][1]["duration_ms"] == 1500.0


@pytest.mark.asyncio
async def test_oneshot_reporter_summary_metrics(mock_oneshot_run, reporter_config):
    """Verify summary metrics calculation."""
    from gavel_ai.reporters.oneshot_reporter import OneShotReporter

    reporter = OneShotReporter(reporter_config)
    context = reporter._build_context(mock_oneshot_run)

    summary = context["summary_metrics"]
    assert "claude" in summary
    assert "gpt" in summary
    assert summary["claude"]["similarity"] == 9.0
    assert summary["gpt"]["similarity"] == 8.0


@pytest.mark.asyncio
async def test_oneshot_reporter_performance_metrics(mock_oneshot_run, reporter_config):
    """Verify performance metrics calculation."""
    from gavel_ai.reporters.oneshot_reporter import OneShotReporter

    reporter = OneShotReporter(reporter_config)
    context = reporter._build_context(mock_oneshot_run)

    perf = context["performance_metrics"]
    assert perf["claude"]["avg_turn_time"] == 1.5
    assert perf["claude"]["total_time"] == 1.5
    assert perf["gpt"]["avg_turn_time"] == 1.2
    assert perf["gpt"]["total_time"] == 1.2
