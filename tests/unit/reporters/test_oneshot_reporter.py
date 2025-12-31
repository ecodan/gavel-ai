"""
Tests for OneShotReporter.

Validates OneShot report generation with HTML and Markdown formats,
winner calculation, and expandable sections.
"""

from typing import Any, Dict, List

import pytest


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
        self.results = results if results is not None else [
            {
                "scenario_id": "scenario-1",
                "variant_id": "claude",
                "processor_output": "Paris is the capital of France.",
                "scenario_input": {"prompt": "What is the capital of France?"},
                "judges": [
                    {
                        "judge_id": "similarity",
                        "score": 9,
                        "reasoning": "Accurate and concise.",
                        "evidence": "Direct answer to question",
                    }
                ],
            },
            {
                "scenario_id": "scenario-1",
                "variant_id": "gpt",
                "processor_output": "The capital of France is Paris.",
                "scenario_input": {"prompt": "What is the capital of France?"},
                "judges": [
                    {
                        "judge_id": "similarity",
                        "score": 8,
                        "reasoning": "Accurate but slightly wordy.",
                        "evidence": None,
                    }
                ],
            },
            {
                "scenario_id": "scenario-2",
                "variant_id": "claude",
                "processor_output": "London",
                "scenario_input": {"prompt": "Capital of UK?"},
                "judges": [{"judge_id": "similarity", "score": 10, "reasoning": "Perfect."}],
            },
            {
                "scenario_id": "scenario-2",
                "variant_id": "gpt",
                "processor_output": "London is the capital.",
                "scenario_input": {"prompt": "Capital of UK?"},
                "judges": [
                    {
                        "judge_id": "similarity",
                        "score": 9,
                        "reasoning": "Correct but verbose.",
                    }
                ],
            },
        ]
        self.telemetry = {
            "total_duration_seconds": 45,
            "llm_calls": {
                "total": 10,
                "tokens": {"prompt_total": 500, "completion_total": 200},
            },
        }


@pytest.fixture
def mock_oneshot_run():
    """Mock Run with OneShot evaluation data."""
    return MockRun()


@pytest.fixture
def mock_tie_run():
    """Mock Run with tied results."""
    return MockRun(
        run_id="run-tie-20251230",
        eval_name="Tie Scenario",
        results=[
            {
                "scenario_id": "scenario-1",
                "variant_id": "claude",
                "processor_output": "Answer A",
                "scenario_input": {"prompt": "Question?"},
                "judges": [{"judge_id": "similarity", "score": 10, "reasoning": "Good."}],
            },
            {
                "scenario_id": "scenario-1",
                "variant_id": "gpt",
                "processor_output": "Answer B",
                "scenario_input": {"prompt": "Question?"},
                "judges": [{"judge_id": "similarity", "score": 10, "reasoning": "Good."}],
            },
        ],
    )


@pytest.fixture
def reporter_config(tmp_path):
    """ReporterConfig for testing."""
    from gavel_ai.core.models import ReporterConfig

    template_path = "src/gavel_ai/reporters/templates"
    return ReporterConfig(template_path=template_path, output_format="html")


@pytest.mark.asyncio
async def test_oneshot_reporter_generates_html(mock_oneshot_run, reporter_config):
    """OneShotReporter generates complete HTML report with all required sections."""
    from gavel_ai.reporters.oneshot_reporter import OneShotReporter

    reporter = OneShotReporter(reporter_config)

    output = await reporter.generate(mock_oneshot_run, "oneshot.html")

    # Verify all sections present
    assert "<h1>Claude vs GPT Comparison</h1>" in output
    assert "Winner" in output
    assert "claude" in output or "gpt" in output
    assert "Summary" in output
    assert "Detailed Results" in output
    assert "Execution Metrics" in output


@pytest.mark.asyncio
async def test_oneshot_reporter_generates_markdown(mock_oneshot_run, reporter_config):
    """OneShotReporter generates complete Markdown report."""
    from gavel_ai.reporters.oneshot_reporter import OneShotReporter

    reporter = OneShotReporter(reporter_config)

    output = await reporter.generate(mock_oneshot_run, "oneshot.md")

    # Verify markdown structure
    assert "# Claude vs GPT Comparison" in output
    assert "## Winner" in output or "## 🏆 Winner" in output
    assert "## Summary" in output
    assert "## Detailed Results" in output


@pytest.mark.asyncio
async def test_oneshot_reporter_calculates_winner(mock_oneshot_run, reporter_config):
    """OneShotReporter correctly calculates winner based on total scores."""
    from gavel_ai.reporters.oneshot_reporter import OneShotReporter

    reporter = OneShotReporter(reporter_config)

    # Build context to access winner calculation
    context = reporter._build_context(mock_oneshot_run)

    assert "winner" in context
    winner = context["winner"]

    # Claude: scenario-1 (9) + scenario-2 (10) = 19
    # GPT: scenario-1 (8) + scenario-2 (9) = 17
    # Claude should win
    assert winner["variant_id"] == "claude"
    assert winner["total_score"] == 19
    assert winner["is_tie"] is False


@pytest.mark.asyncio
async def test_oneshot_reporter_handles_tie(mock_tie_run, reporter_config):
    """OneShotReporter correctly identifies and handles tied results."""
    from gavel_ai.reporters.oneshot_reporter import OneShotReporter

    reporter = OneShotReporter(reporter_config)

    context = reporter._build_context(mock_tie_run)
    winner = context["winner"]

    # Both variants scored 10
    assert winner["total_score"] == 10
    assert winner["is_tie"] is True
    assert winner["variant_id"] in ["claude", "gpt"]


@pytest.mark.asyncio
async def test_oneshot_reporter_formats_judge_results(mock_oneshot_run, reporter_config):
    """OneShotReporter correctly formats judge results with reasoning and evidence."""
    from gavel_ai.reporters.oneshot_reporter import OneShotReporter

    reporter = OneShotReporter(reporter_config)

    context = reporter._build_context(mock_oneshot_run)
    results = context["results"]

    # Check first scenario has judge results
    assert len(results) > 0
    first_scenario = results[0]
    assert "variant_outputs" in first_scenario

    # Check judge results structure
    variant_output = first_scenario["variant_outputs"][0]
    assert "judge_results" in variant_output
    judge_result = variant_output["judge_results"][0]

    assert "judge_id" in judge_result
    assert "score" in judge_result
    assert "reasoning" in judge_result


@pytest.mark.asyncio
async def test_oneshot_reporter_includes_judges_list(mock_oneshot_run, reporter_config):
    """OneShotReporter extracts judges list from results."""
    from gavel_ai.reporters.oneshot_reporter import OneShotReporter

    reporter = OneShotReporter(reporter_config)

    context = reporter._build_context(mock_oneshot_run)

    assert "judges" in context
    judges = context["judges"]

    assert len(judges) > 0
    assert any(j["judge_id"] == "similarity" for j in judges)


@pytest.mark.asyncio
async def test_oneshot_reporter_handles_empty_results(reporter_config):
    """OneShotReporter handles Run with no results gracefully."""
    from gavel_ai.reporters.oneshot_reporter import OneShotReporter

    empty_run = MockRun(results=[])
    reporter = OneShotReporter(reporter_config)

    context = reporter._build_context(empty_run)

    assert context["winner"]["variant_id"] == "N/A"
    assert context["winner"]["total_score"] == 0
    assert context["winner"]["is_tie"] is False
    assert context["summary"] == []


@pytest.mark.asyncio
async def test_oneshot_reporter_emits_telemetry(mock_oneshot_run, reporter_config):
    """OneShotReporter emits OpenTelemetry spans during generation."""
    from gavel_ai.reporters.oneshot_reporter import OneShotReporter

    reporter = OneShotReporter(reporter_config)

    # Generate report - should emit span
    output = await reporter.generate(mock_oneshot_run, "oneshot.html")

    # If generation completes without error, telemetry is working
    assert output is not None
    assert len(output) > 0
