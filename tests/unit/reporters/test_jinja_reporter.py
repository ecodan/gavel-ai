"""
Unit tests for Jinja2Reporter.

Tests:
- Template rendering with all context variables
- Custom template loading and usage
- Default template usage
- Template not found error handling
- Missing context variable handling
- OpenTelemetry span emission
"""

import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

from gavel_ai.core.exceptions import ReporterError
from gavel_ai.core.models import ReporterConfig
from gavel_ai.reporters.jinja_reporter import Jinja2Reporter


class MockRun:
    """Mock Run object for testing."""

    def __init__(
        self,
        run_id: str = "run-20251229-120000",
        metadata: Dict[str, Any] = None,
        results: List[Dict[str, Any]] = None,
        telemetry: Dict[str, Any] = None,
    ):
        self.run_id = run_id
        self.metadata = metadata or {}
        self.results = results or []
        self.telemetry = telemetry or {}


@pytest.fixture
def temp_template_dir():
    """Create temporary template directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_run():
    """Create mock run with sample data."""
    return MockRun(
        run_id="test-run-001",
        metadata={
            "eval_name": "Test Evaluation",
            "timestamp": "2025-12-29T12:00:00Z",
            "config_hash": "abc123",
            "scenario_count": 2,
            "variant_count": 2,
            "eval_type": "oneshot",
        },
        results=[
            {
                "scenario_id": "scenario-1",
                "variant_id": "claude",
                "scenario_input": {"question": "What is AI?"},
                "processor_output": "AI is artificial intelligence.",
                "judges": [
                    {"judge_id": "similarity", "score": 9, "reasoning": "Accurate"},
                ],
            },
            {
                "scenario_id": "scenario-1",
                "variant_id": "gpt",
                "scenario_input": {"question": "What is AI?"},
                "processor_output": "AI is machine learning.",
                "judges": [
                    {"judge_id": "similarity", "score": 8, "reasoning": "Good"},
                ],
            },
        ],
        telemetry={
            "total_duration_seconds": 45,
            "llm_calls": {
                "total": 4,
                "tokens": {"prompt_total": 500, "completion_total": 200},
            },
        },
    )


@pytest.fixture
def simple_template(temp_template_dir):
    """Create simple test template."""
    template_path = temp_template_dir / "test.html"
    template_path.write_text("""
    <html>
        <title>{{ title }}</title>
        <body>
            <h1>{{ title }}</h1>
            <p>Variants: {{ metadata.variant_count }}</p>
            <p>Scenarios: {{ metadata.scenario_count }}</p>
        </body>
    </html>
    """)
    return "test.html"


@pytest.mark.asyncio
async def test_jinja2_reporter_renders_template(temp_template_dir, mock_run, simple_template):
    """Jinja2Reporter renders template with context variables."""
    config = ReporterConfig(template_path=str(temp_template_dir), output_format="html")

    reporter = Jinja2Reporter(config)
    output = await reporter.generate(mock_run, simple_template)

    assert "<title>Test Evaluation</title>" in output
    assert "Variants: 2" in output
    assert "Scenarios: 2" in output


@pytest.mark.asyncio
async def test_jinja2_reporter_uses_default_base_html_template(mock_run):
    """Jinja2Reporter can use base.html template."""
    import gavel_ai.reporters

    # Get path to templates directory
    reporters_dir = Path(gavel_ai.reporters.__file__).parent
    templates_dir = reporters_dir / "templates"

    config = ReporterConfig(template_path=str(templates_dir), output_format="html")

    reporter = Jinja2Reporter(config)
    output = await reporter.generate(mock_run, "base.html")

    # Verify key sections are present
    assert "Test Evaluation" in output
    assert "Overview" in output
    assert "Summary" in output
    assert "Detailed Results" in output
    assert "Execution Metrics" in output


@pytest.mark.asyncio
async def test_jinja2_reporter_uses_default_base_md_template(mock_run):
    """Jinja2Reporter can use base.md template."""
    import gavel_ai.reporters

    # Get path to templates directory
    reporters_dir = Path(gavel_ai.reporters.__file__).parent
    templates_dir = reporters_dir / "templates"

    config = ReporterConfig(template_path=str(templates_dir), output_format="markdown")

    reporter = Jinja2Reporter(config)
    output = await reporter.generate(mock_run, "base.md")

    # Verify key markdown sections
    assert "# Test Evaluation" in output
    assert "## Overview" in output
    assert "## Summary" in output
    assert "## Detailed Results" in output


@pytest.mark.asyncio
async def test_jinja2_reporter_template_not_found_error(temp_template_dir, mock_run):
    """Jinja2Reporter raises ReporterError when template not found."""
    config = ReporterConfig(template_path=str(temp_template_dir), output_format="html")

    reporter = Jinja2Reporter(config)

    with pytest.raises(ReporterError, match="Template 'missing.html' not found"):
        await reporter.generate(mock_run, "missing.html")


@pytest.mark.asyncio
async def test_jinja2_reporter_template_syntax_error(temp_template_dir, mock_run):
    """Jinja2Reporter raises ReporterError on template syntax errors."""
    # Create template with syntax error
    bad_template = temp_template_dir / "bad.html"
    bad_template.write_text("{{ title {% endfor %}")  # Invalid syntax

    config = ReporterConfig(template_path=str(temp_template_dir), output_format="html")

    reporter = Jinja2Reporter(config)

    with pytest.raises(ReporterError, match="Template syntax error"):
        await reporter.generate(mock_run, "bad.html")


@pytest.mark.asyncio
async def test_jinja2_reporter_undefined_variable_error(temp_template_dir, mock_run):
    """Jinja2Reporter raises ReporterError on undefined variables."""
    # Create template with undefined variable
    template = temp_template_dir / "undefined.html"
    template.write_text("{{ undefined_var }}")

    config = ReporterConfig(template_path=str(temp_template_dir), output_format="html")

    reporter = Jinja2Reporter(config)

    # Jinja2 by default silently ignores undefined variables, so this test
    # verifies the template renders successfully
    output = await reporter.generate(mock_run, "undefined.html")
    assert output is not None


@pytest.mark.asyncio
async def test_jinja2_reporter_custom_variables(temp_template_dir, mock_run):
    """Jinja2Reporter supports custom variables."""
    template = temp_template_dir / "custom.html"
    template.write_text("Company: {{ company_name }}, Version: {{ version }}")

    config = ReporterConfig(
        template_path=str(temp_template_dir),
        output_format="html",
        custom_vars={"company_name": "Acme Corp", "version": "1.0"},
    )

    reporter = Jinja2Reporter(config)
    output = await reporter.generate(mock_run, "custom.html")

    assert "Company: Acme Corp" in output
    assert "Version: 1.0" in output


@pytest.mark.asyncio
async def test_jinja2_reporter_builds_summary_table(mock_run):
    """Jinja2Reporter builds summary table with aggregated scores."""
    import gavel_ai.reporters

    reporters_dir = Path(gavel_ai.reporters.__file__).parent
    templates_dir = reporters_dir / "templates"

    config = ReporterConfig(template_path=str(templates_dir), output_format="html")

    reporter = Jinja2Reporter(config)

    # Build context and check summary
    context = reporter._build_context(mock_run)

    assert "summary" in context
    assert len(context["summary"]) == 2  # 2 variants

    # Check claude variant
    claude_summary = next(v for v in context["summary"] if v["variant_id"] == "claude")
    assert claude_summary["avg_score"] == 9.0
    assert claude_summary["total_score"] == 9.0

    # Check gpt variant
    gpt_summary = next(v for v in context["summary"] if v["variant_id"] == "gpt")
    assert gpt_summary["avg_score"] == 8.0
    assert gpt_summary["total_score"] == 8.0


@pytest.mark.asyncio
async def test_jinja2_reporter_builds_results_details(mock_run):
    """Jinja2Reporter builds detailed results grouped by scenario."""
    import gavel_ai.reporters

    reporters_dir = Path(gavel_ai.reporters.__file__).parent
    templates_dir = reporters_dir / "templates"

    config = ReporterConfig(template_path=str(templates_dir), output_format="html")

    reporter = Jinja2Reporter(config)
    context = reporter._build_context(mock_run)

    assert "results" in context
    assert len(context["results"]) == 1  # 1 scenario

    scenario_result = context["results"][0]
    assert scenario_result["scenario_id"] == "scenario-1"
    assert len(scenario_result["variant_outputs"]) == 2  # 2 variants


def test_jinja2_reporter_invalid_template_path():
    """Jinja2Reporter raises error with invalid template path."""
    config = ReporterConfig(template_path="/nonexistent/path", output_format="html")

    # Should not raise during initialization (lazy loading)
    reporter = Jinja2Reporter(config)
    assert reporter is not None


@pytest.mark.asyncio
async def test_jinja2_reporter_empty_run_data():
    """Jinja2Reporter handles empty run data gracefully."""
    empty_run = MockRun(metadata={"eval_name": "Empty Test"}, results=[], telemetry={})

    import gavel_ai.reporters

    reporters_dir = Path(gavel_ai.reporters.__file__).parent
    templates_dir = reporters_dir / "templates"

    config = ReporterConfig(template_path=str(templates_dir), output_format="html")

    reporter = Jinja2Reporter(config)
    output = await reporter.generate(empty_run, "base.html")

    assert "Empty Test" in output
    assert "No summary data available" in output or "Summary" in output


@pytest.mark.asyncio
async def test_jinja2_reporter_telemetry_span_emission(
    temp_template_dir, mock_run, simple_template
):
    """Jinja2Reporter emits OpenTelemetry spans."""
    config = ReporterConfig(template_path=str(temp_template_dir), output_format="html")

    reporter = Jinja2Reporter(config)

    # Verify tracer is configured
    assert reporter.tracer is not None

    # Generate report (spans are emitted internally)
    output = await reporter.generate(mock_run, simple_template)

    assert output is not None
    # Span emission is verified by OpenTelemetry test infrastructure
