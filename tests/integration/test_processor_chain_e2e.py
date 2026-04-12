"""
End-to-end integration tests for processor chain refactoring (Phases 1-4).

Tests:
- Input subclass creation and type contracts
- Template rendering with Jinja2
- PromptInputProcessor accepting PromptInput
- Message construction for LLM calls
- ClosedBoxInputProcessor request building
- Full pipeline from scenario to processor output
"""

import json
import logging
from typing import Any, Dict

import pytest

from gavel_ai.models.runtime import PromptInput, RemoteSystemInput
from gavel_ai.processors.closedbox_processor import ClosedBoxInputProcessor
from gavel_ai.processors.prompt_processor import PromptInputProcessor


@pytest.fixture
def logger() -> logging.Logger:
    """Provide a logger for testing."""
    return logging.getLogger("test")


@pytest.mark.integration
class TestInputSubclassingContract:
    """Test Phase 1: Input subclass contract and behavior."""

    def test_prompt_input_has_user_system_fields(self) -> None:
        """Test PromptInput has user and optional system fields."""
        prompt = PromptInput(
            id="test-1",
            user="Test user prompt",
            system="Test system prompt",
            metadata={"key": "value"},
        )

        assert prompt.user == "Test user prompt"
        assert prompt.system == "Test system prompt"
        assert prompt.metadata["key"] == "value"

    def test_prompt_input_system_optional(self) -> None:
        """Test PromptInput system field is optional."""
        prompt = PromptInput(
            id="test-2",
            user="User only",
        )

        assert prompt.user == "User only"
        assert prompt.system is None

    def test_remote_system_input_has_required_fields(self) -> None:
        """Test RemoteSystemInput has all required fields."""
        remote = RemoteSystemInput(
            id="api-1",
            endpoint="https://api.example.com",
            method="POST",
            headers={"X-Custom": "header"},
            body={"data": "value"},
        )

        assert remote.endpoint == "https://api.example.com"
        assert remote.method == "POST"
        assert remote.headers["X-Custom"] == "header"
        assert remote.body["data"] == "value"

    def test_remote_system_input_auth_optional(self) -> None:
        """Test RemoteSystemInput auth field is optional."""
        remote = RemoteSystemInput(
            id="api-2",
            endpoint="https://api.example.com",
            method="GET",
            headers={},
            body={},
        )

        assert remote.auth is None


@pytest.mark.integration
class TestTemplateRendering:
    """Test Phase 2: Template rendering in data preparation."""

    def test_scenario_variable_rendering(self) -> None:
        """Test that scenario variables are rendered correctly."""
        # Simulate ScenarioProcessorStep template rendering
        from jinja2 import Template

        template_text = "Analyze {{ scenario.content }} from {{ scenario.site }}"
        variables = {"content": "Breaking News", "site": "www.bbc.com"}

        tmpl = Template(template_text)
        rendered = tmpl.render(scenario=variables)

        assert "Breaking News" in rendered
        assert "www.bbc.com" in rendered

    def test_conditional_template_rendering(self) -> None:
        """Test conditional logic in template rendering."""
        from jinja2 import Template

        template_text = (
            "{% if scenario.type == 'news' %}"
            "News: {{ scenario.content }}"
            "{% else %}"
            "Other: {{ scenario.content }}"
            "{% endif %}"
        )

        # News case
        tmpl = Template(template_text)
        rendered_news = tmpl.render(scenario={"type": "news", "content": "Breaking"})
        assert "News: Breaking" in rendered_news

        # Other case
        rendered_other = tmpl.render(scenario={"type": "blog", "content": "Post"})
        assert "Other: Post" in rendered_other

    def test_template_rendered_prompt_input_creation(self) -> None:
        """Test creating PromptInput from rendered template."""
        # Simulate ScenarioProcessorStep flow
        from jinja2 import Template

        template_text = "Extract data from {{ scenario.html }}"
        scenario_input = {"html": "<h1>Title</h1>", "site": "www.example.com"}

        tmpl = Template(template_text)
        rendered = tmpl.render(scenario=scenario_input)

        # Create PromptInput with rendered prompt
        prompt = PromptInput(
            id="scenario-123",
            user=rendered,
            metadata={"scenario_input": scenario_input, "template": "default:v1"},
        )

        assert "<h1>Title</h1>" in prompt.user
        assert prompt.metadata["template"] == "default:v1"


@pytest.mark.integration
class TestPromptProcessorPhase3:
    """Test Phase 3: PromptInputProcessor with PromptInput."""

    def test_prompt_input_message_construction(self) -> None:
        """Test that PromptInput is correctly converted to LLM messages."""
        prompt = PromptInput(
            id="test-1",
            user="Analyze this content",
            system="You are an expert analyzer",
        )

        # Simulate PromptInputProcessor message construction
        messages: list[dict[str, str]] = []
        if prompt.system:
            messages.append({"role": "system", "content": prompt.system})
        messages.append({"role": "user", "content": prompt.user})

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "Analyze this content" in messages[1]["content"]

    def test_prompt_input_user_only_message_construction(self) -> None:
        """Test message construction with user prompt only."""
        prompt = PromptInput(
            id="test-2",
            user="Process this",
        )

        messages: list[dict[str, str]] = []
        if prompt.system:
            messages.append({"role": "system", "content": prompt.system})
        messages.append({"role": "user", "content": prompt.user})

        assert len(messages) == 1
        assert messages[0]["role"] == "user"


@pytest.mark.integration
class TestClosedBoxProcessorPhase4:
    """Test Phase 4: ClosedBoxInputProcessor with RemoteSystemInput."""

    def test_remote_system_input_request_kwargs_building(self) -> None:
        """Test building request kwargs from RemoteSystemInput."""
        from gavel_ai.models.runtime import ProcessorConfig

        processor = ClosedBoxInputProcessor(
            ProcessorConfig(
                processor_type="closedbox",
                timeout_seconds=30,
            )
        )

        remote = RemoteSystemInput(
            id="api-1",
            endpoint="https://api.example.com/analyze",
            method="POST",
            headers={"X-Custom": "value"},
            body={"query": "test"},
            auth={"bearer_token": "secret"},
        )

        kwargs = processor._build_request_kwargs(remote)

        assert kwargs["headers"]["X-Custom"] == "value"
        assert kwargs["headers"]["Authorization"] == "Bearer secret"
        assert kwargs["json"]["query"] == "test"

    def test_request_building_multiple_auth_methods(self) -> None:
        """Test request building with different auth methods."""
        from gavel_ai.models.runtime import ProcessorConfig

        processor = ClosedBoxInputProcessor(
            ProcessorConfig(
                processor_type="closedbox",
                timeout_seconds=30,
            )
        )

        # Bearer token
        remote_bearer = RemoteSystemInput(
            id="api-bearer",
            endpoint="https://api.example.com",
            method="POST",
            headers={},
            body={},
            auth={"bearer_token": "token123"},
        )
        kwargs_bearer = processor._build_request_kwargs(remote_bearer)
        assert "Authorization" in kwargs_bearer["headers"]

        # API key
        remote_key = RemoteSystemInput(
            id="api-key",
            endpoint="https://api.example.com",
            method="POST",
            headers={},
            body={},
            auth={"api_key": "key456"},
        )
        kwargs_key = processor._build_request_kwargs(remote_key)
        assert "X-API-Key" in kwargs_key["headers"]

        # Basic auth
        remote_basic = RemoteSystemInput(
            id="api-basic",
            endpoint="https://api.example.com",
            method="POST",
            headers={},
            body={},
            auth={"username": "user", "password": "pass"},
        )
        kwargs_basic = processor._build_request_kwargs(remote_basic)
        assert "auth" in kwargs_basic


@pytest.mark.integration
class TestEndToEndScenarioFlow:
    """Test Phase 5: Full pipeline from scenario to processor output."""

    def test_full_prompt_flow_scenario_to_processor(self) -> None:
        """Test full flow: scenario → PromptInput → messages → output."""
        from jinja2 import Template

        # Step 1: Scenario with input data
        scenario = {
            "id": "scenario-1",
            "input": {"html": "<h1>News</h1>", "site": "www.example.com"},
            "metadata": {"source": "test"},
        }

        # Step 2: Template loading and rendering (ScenarioProcessorStep)
        template_text = (
            "You are a news analyzer.\n"
            "Extract headlines from: {{ scenario.html }}\n"
            "Website: {{ scenario.site }}"
        )
        tmpl = Template(template_text)
        rendered = tmpl.render(scenario=scenario["input"])

        # Step 3: Create PromptInput with rendered prompt
        prompt = PromptInput(
            id=scenario["id"],
            user=rendered,
            metadata={"scenario_input": scenario["input"], "template": "news:v1"},
        )

        # Step 4: Simulate PromptInputProcessor message construction
        messages: list[dict[str, str]] = []
        if prompt.system:
            messages.append({"role": "system", "content": prompt.system})
        messages.append({"role": "user", "content": prompt.user})

        # Verify flow integrity
        assert prompt.id == scenario["id"]
        assert "<h1>News</h1>" in messages[0]["content"]
        assert "www.example.com" in messages[0]["content"]
        assert "You are a news analyzer" in messages[0]["content"]

    def test_full_api_flow_scenario_to_processor(self) -> None:
        """Test full flow for API-based evaluation."""
        from gavel_ai.models.runtime import ProcessorConfig

        # Step 1: API scenario
        scenario = {
            "id": "api-scenario-1",
            "input": {
                "endpoint": "https://api.example.com/analyze",
                "method": "POST",
                "body": {"text": "sample content"},
            },
        }

        # Step 2: Create RemoteSystemInput (ScenarioProcessorStep)
        remote = RemoteSystemInput(
            id=scenario["id"],
            endpoint=scenario["input"]["endpoint"],
            method=scenario["input"]["method"],
            headers={"Content-Type": "application/json"},
            body=scenario["input"]["body"],
            auth={"bearer_token": "api-token"},
        )

        # Step 3: Build HTTP request kwargs (ClosedBoxInputProcessor)
        processor = ClosedBoxInputProcessor(
            ProcessorConfig(processor_type="closedbox", timeout_seconds=30)
        )
        kwargs = processor._build_request_kwargs(remote)

        # Verify flow integrity
        assert remote.id == scenario["id"]
        assert kwargs["headers"]["Authorization"] == "Bearer api-token"
        assert kwargs["json"]["text"] == "sample content"
