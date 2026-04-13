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
    """Test ScenarioProcessorStep functionality (uses string.Template syntax)."""

    def test_render_template_basic(self, step: ScenarioProcessorStep) -> None:
        """Test basic template rendering with dict variables."""
        template = "Extract headlines from: $html"
        variables = {"html": "<h1>Breaking News</h1>"}

        result = step._render_template(template, variables)

        assert result == "Extract headlines from: <h1>Breaking News</h1>"

    def test_render_template_braced_syntax(self, step: ScenarioProcessorStep) -> None:
        """Test template rendering with ${var} braced syntax."""
        template = "Site: ${site}, Count: ${count}"
        variables = {"site": "www.example.com", "count": "3"}

        result = step._render_template(template, variables)

        assert result == "Site: www.example.com, Count: 3"

    def test_render_template_multiple_vars(self, step: ScenarioProcessorStep) -> None:
        """Test template rendering with multiple variables."""
        template = "Analyze $site: $content"
        variables = {"site": "news.com", "content": "Breaking story"}

        result = step._render_template(template, variables)

        assert "news.com" in result
        assert "Breaking story" in result

    def test_render_template_missing_variable(self, step: ScenarioProcessorStep) -> None:
        """Test that missing variable raises ProcessorError."""
        template = "Site: $site, HTML: $html"
        variables = {"site": "www.example.com"}  # html is missing

        with pytest.raises(ProcessorError, match="not found in scenario"):
            step._render_template(template, variables)

    def test_render_template_invalid_syntax_error(self, step: ScenarioProcessorStep) -> None:
        """Test that malformed template placeholder raises ProcessorError."""
        template = "bad placeholder: $"
        variables = {"site": "www.example.com"}

        with pytest.raises(ProcessorError, match="Malformed template placeholder"):
            step._render_template(template, variables)

    def test_render_template_empty_variables(self, step: ScenarioProcessorStep) -> None:
        """Test template rendering with no substitution markers."""
        template = "Process this static prompt"
        variables: dict = {}

        result = step._render_template(template, variables)

        assert result == "Process this static prompt"

    def test_render_template_complex_flat_vars(
        self, step: ScenarioProcessorStep
    ) -> None:
        """Test template rendering with multiple flat variables."""
        template = "Domain: $domain, Topic: $topic, Sentiment: $sentiment"
        variables = {
            "domain": "news.com",
            "topic": "technology",
            "sentiment": "positive",
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
            "HTML Content:\n$html\n\n"
            "Website: $site"
        )
        variables = {
            "html": "<h1>Breaking News</h1>\n<h2>Story 2</h2>",
            "site": "www.bbc.com",
        }

        result = step._render_template(template, variables)

        assert "You are a news content analyzer" in result
        assert "Breaking News" in result
        assert "www.bbc.com" in result
        assert "$" not in result  # No unrendered variables

    def test_render_api_call_prompt(self, step: ScenarioProcessorStep) -> None:
        """Test rendering a prompt for API-based evaluation."""
        template = (
            "Call the following API:\n"
            "Endpoint: $endpoint\n"
            "Method: $method\n"
            "Body: $body"
        )
        variables = {
            "endpoint": "https://api.example.com/analyze",
            "method": "POST",
            "body": '{"text": "sample", "language": "en"}',
        }

        result = step._render_template(template, variables)

        assert "https://api.example.com/analyze" in result
        assert "POST" in result
        assert "sample" in result
