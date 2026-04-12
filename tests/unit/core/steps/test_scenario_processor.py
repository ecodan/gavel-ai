"""
Unit tests for ScenarioProcessorStep template rendering.

Tests:
- Template rendering with various variable formats
- Error handling for missing/invalid templates
- PromptInput creation with metadata
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gavel_ai.core.exceptions import ConfigError, ProcessorError
from gavel_ai.core.steps.scenario_processor import ScenarioProcessorStep
from gavel_ai.models.runtime import PromptInput


@pytest.fixture
def logger() -> logging.Logger:
    """Provide a logger for testing."""
    return logging.getLogger("test")


@pytest.fixture
def step(logger: logging.Logger) -> ScenarioProcessorStep:
    """Provide a ScenarioProcessorStep instance."""
    return ScenarioProcessorStep(logger)


@pytest.mark.unit
class TestScenarioProcessorStep:
    """Test ScenarioProcessorStep functionality."""

    def test_render_template_basic(self, step: ScenarioProcessorStep) -> None:
        """Test basic template rendering with dict variables."""
        template = "Extract headlines from: {{ scenario.html }}"
        variables = {"html": "<h1>Breaking News</h1>"}

        result = step._render_template(template, variables)

        assert result == "Extract headlines from: <h1>Breaking News</h1>"

    def test_render_template_with_loop(self, step: ScenarioProcessorStep) -> None:
        """Test template rendering with loop over list."""
        template = (
            "Analyze {{ scenario.site }} content:\n"
            "{% for item in scenario.articles %}"
            "- {{ item }}\n"
            "{% endfor %}"
        )
        variables = {
            "site": "www.example.com",
            "articles": ["Article 1", "Article 2"],
        }

        result = step._render_template(template, variables)

        assert "www.example.com" in result
        assert "Article 1" in result
        assert "Article 2" in result

    def test_render_template_conditional(self, step: ScenarioProcessorStep) -> None:
        """Test template rendering with conditional logic."""
        template = (
            "{% if scenario.type == 'news' %}"
            "Analyze this news article: {{ scenario.content }}"
            "{% else %}"
            "Process this content: {{ scenario.content }}"
            "{% endif %}"
        )

        variables_news = {"type": "news", "content": "Breaking news here"}
        variables_other = {"type": "blog", "content": "Blog post here"}

        result_news = step._render_template(template, variables_news)
        result_other = step._render_template(template, variables_other)

        assert "Analyze this news article" in result_news
        assert "Process this content" in result_other

    def test_render_template_missing_variable(self, step: ScenarioProcessorStep) -> None:
        """Test that missing variables render as empty."""
        template = "Site: {{ scenario.site }}, HTML: {{ scenario.html }}"
        variables = {"site": "www.example.com"}  # html is missing

        result = step._render_template(template, variables)

        assert "www.example.com" in result
        assert result.endswith(", HTML: ")  # html renders as empty string

    def test_render_template_invalid_syntax_error(self, step: ScenarioProcessorStep) -> None:
        """Test that invalid Jinja2 syntax raises ProcessorError."""
        template = "{{ scenario.site | undefined_filter }}"
        variables = {"site": "www.example.com"}

        with pytest.raises(ProcessorError, match="Failed to render prompt template"):
            step._render_template(template, variables)

    def test_render_template_empty_variables(self, step: ScenarioProcessorStep) -> None:
        """Test template rendering with empty variables dict."""
        template = "Process this: {{ scenario }}"
        variables: dict = {}

        result = step._render_template(template, variables)

        # Should render without error, with empty scenario
        assert "Process this:" in result

    def test_render_template_complex_nested_structure(
        self, step: ScenarioProcessorStep
    ) -> None:
        """Test template rendering with complex nested variables."""
        template = (
            "Analyze {{ scenario.metadata.domain }} with context:\n"
            "{% for ctx in scenario.metadata.contexts %}"
            "- {{ ctx.name }}: {{ ctx.value }}\n"
            "{% endfor %}"
        )
        variables = {
            "metadata": {
                "domain": "news.com",
                "contexts": [
                    {"name": "topic", "value": "technology"},
                    {"name": "sentiment", "value": "positive"},
                ],
            }
        }

        result = step._render_template(template, variables)

        assert "news.com" in result
        assert "technology" in result
        assert "positive" in result

    def test_prompt_input_creation_with_metadata(self) -> None:
        """Test PromptInput creation with preserved metadata."""
        prompt_input = PromptInput(
            id="scenario-1",
            user="Extracted prompt",
            system=None,
            metadata={
                "scenario_input": {"html": "...", "site": "example.com"},
                "template": "default:v1",
                "original_metadata_key": "value",
            },
        )

        assert prompt_input.id == "scenario-1"
        assert prompt_input.user == "Extracted prompt"
        assert prompt_input.system is None
        assert prompt_input.metadata["template"] == "default:v1"
        assert prompt_input.metadata["original_metadata_key"] == "value"

    def test_prompt_input_json_roundtrip(self) -> None:
        """Test PromptInput can be serialized and deserialized."""
        original = PromptInput(
            id="scenario-1",
            user="Extracted prompt with {{ variable }}",
            system="System instructions",
            metadata={"key": "value"},
        )

        # Serialize to dict
        data = original.model_dump()
        assert data["user"] == "Extracted prompt with {{ variable }}"
        assert data["system"] == "System instructions"

        # Deserialize from dict
        restored = PromptInput(**data)
        assert restored.id == original.id
        assert restored.user == original.user
        assert restored.system == original.system
        assert restored.metadata == original.metadata


@pytest.mark.unit
class TestScenarioProcessorStepIntegration:
    """Integration tests for template rendering scenarios."""

    def test_render_headline_extraction_prompt(self, step: ScenarioProcessorStep) -> None:
        """Test rendering a realistic headline extraction prompt."""
        template = (
            "You are a news content analyzer. Extract headlines from the following HTML.\n"
            "Return ONLY a JSON object with a 'stories' array.\n\n"
            "HTML Content:\n{{ scenario.html }}\n\n"
            "Website: {{ scenario.site }}"
        )
        variables = {
            "html": "<h1>Breaking News</h1>\n<h2>Story 2</h2>",
            "site": "www.bbc.com",
        }

        result = step._render_template(template, variables)

        assert "You are a news content analyzer" in result
        assert "Breaking News" in result
        assert "www.bbc.com" in result
        assert "{{ scenario" not in result  # No unrendered variables

    def test_render_api_call_prompt(self, step: ScenarioProcessorStep) -> None:
        """Test rendering a prompt for API-based evaluation."""
        template = (
            "Call the following API:\n"
            "Endpoint: {{ scenario.endpoint }}\n"
            "Method: {{ scenario.method }}\n"
            "Body: {{ scenario.body | tojson }}"
        )
        variables = {
            "endpoint": "https://api.example.com/analyze",
            "method": "POST",
            "body": {"text": "sample", "language": "en"},
        }

        result = step._render_template(template, variables)

        assert "https://api.example.com/analyze" in result
        assert "POST" in result
        assert '"text": "sample"' in result or "'text': 'sample'" in result
