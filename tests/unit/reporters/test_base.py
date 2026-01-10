"""
Unit tests for Reporter base class and ReporterConfig model.

Tests:
- Reporter ABC cannot be instantiated directly
- Concrete implementations must implement generate method
- ReporterConfig validation (valid and invalid cases)
- ReporterError is raised with proper format
"""

import pytest
from pydantic import ValidationError

from gavel_ai.core.exceptions import ReporterError
from gavel_ai.core.models import ReporterConfig
from gavel_ai.reporters.base import Reporter


def test_reporter_abc_cannot_be_instantiated():
    """Reporter ABC cannot be instantiated directly."""
    config = ReporterConfig(template_path="templates/", output_format="html")

    with pytest.raises(TypeError, match="Can't instantiate abstract class Reporter"):
        Reporter(config)  # type: ignore


def test_concrete_reporter_must_implement_generate():
    """Concrete implementations must implement generate method."""

    class BadReporter(Reporter):
        """Reporter implementation that doesn't implement generate."""

        pass

    config = ReporterConfig(template_path="templates/", output_format="html")

    with pytest.raises(TypeError, match="Can't instantiate abstract class BadReporter"):
        BadReporter(config)  # type: ignore


def test_concrete_reporter_can_be_instantiated():
    """Concrete implementations that implement generate can be instantiated."""

    class GoodReporter(Reporter):
        """Valid reporter implementation."""

        async def generate(self, run, template: str) -> str:
            """Generate report."""
            return "<html>Report</html>"

    config = ReporterConfig(template_path="templates/", output_format="html")

    reporter = GoodReporter(config)
    assert reporter.config == config
    assert reporter.tracer is not None


@pytest.mark.asyncio
async def test_concrete_reporter_generate_method():
    """Concrete reporter generate method can be called."""

    class TestReporter(Reporter):
        """Test reporter implementation."""

        async def generate(self, run, template: str) -> str:
            """Generate report."""
            return f"<html>Report for {template}</html>"

    config = ReporterConfig(template_path="templates/", output_format="html")

    reporter = TestReporter(config)
    result = await reporter.generate(run=None, template="test.html")
    assert result == "<html>Report for test.html</html>"


def test_reporter_config_valid():
    """ReporterConfig validates with required fields."""
    config = ReporterConfig(template_path="templates/", output_format="html")

    assert config.template_path == "templates/"
    assert config.output_format == "html"
    assert config.custom_vars is None


def test_reporter_config_with_custom_vars():
    """ReporterConfig accepts optional custom_vars."""
    config = ReporterConfig(
        template_path="templates/",
        output_format="markdown",
        custom_vars={"company_name": "Acme Corp", "version": "1.0"},
    )

    assert config.template_path == "templates/"
    assert config.output_format == "markdown"
    assert config.custom_vars == {"company_name": "Acme Corp", "version": "1.0"}


def test_reporter_config_missing_required_field():
    """ReporterConfig raises ValidationError when required field is missing."""
    with pytest.raises(ValidationError, match="template_path"):
        ReporterConfig(output_format="html")  # Missing template_path

    with pytest.raises(ValidationError, match="output_format"):
        ReporterConfig(template_path="templates/")  # Missing output_format


def test_reporter_config_extra_fields_ignored():
    """ReporterConfig ignores unknown fields (forward compatible)."""
    config = ReporterConfig(
        template_path="templates/",
        output_format="html",
        unknown_field="this should be ignored",  # type: ignore
        future_feature=42,  # type: ignore
    )

    assert config.template_path == "templates/"
    assert config.output_format == "html"
    # Unknown fields are silently ignored
    assert not hasattr(config, "unknown_field")
    assert not hasattr(config, "future_feature")


def test_reporter_error_inherits_from_gavel_error():
    """ReporterError inherits from GavelError."""
    from gavel_ai.core.exceptions import GavelError

    error = ReporterError("Test error message")
    assert isinstance(error, GavelError)
    assert isinstance(error, Exception)


def test_reporter_error_message_format():
    """ReporterError follows required message format."""
    error_msg = (
        "Template file not found at templates/report.html - "
        "Create template file or check template_path in config"
    )

    error = ReporterError(error_msg)

    assert "Template file not found" in str(error)
    assert "Create template file or check template_path" in str(error)
    assert " - " in str(error)  # Format separator


def test_reporter_error_can_be_raised():
    """ReporterError can be raised and caught."""
    with pytest.raises(ReporterError, match="Template rendering failed"):
        raise ReporterError("Template rendering failed - Check template syntax and context data")


def test_reporter_error_with_chaining():
    """ReporterError can be chained from other exceptions."""
    try:
        # Simulate a Jinja2 error
        raise ValueError("Undefined variable 'title'")
    except ValueError as e:
        with pytest.raises(ReporterError, match="Template rendering failed"):
            raise ReporterError("Template rendering failed - Check context variables") from e
