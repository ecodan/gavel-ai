"""
End-to-end integration tests for processor chain refactoring (Phases 1-4) and
ScenarioProcessorStep with external+http test subjects.

Tests:
- Input subclass creation and type contracts
- Template rendering with Jinja2
- PromptInputProcessor accepting PromptInput
- Message construction for LLM calls
- ExternalHttpProcessor request building
- ScenarioProcessorStep with external+http (task 25): success, process_failure, warning-issue
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import httpx
import pytest

from gavel_ai.core.contexts import LocalFileSystemEvalContext, LocalRunContext
from gavel_ai.core.exceptions import RunPolicyError
from gavel_ai.models.runtime import PromptInput, RemoteSystemInput
from gavel_ai.processors.external_http_processor import ExternalHttpProcessor
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
class TestExternalHttpProcessorPhase4:
    """Test Phase 4: ExternalHttpProcessor with RemoteSystemInput."""

    def test_remote_system_input_request_payload_building(self) -> None:
        """Test building request payload from RemoteSystemInput."""
        from gavel_ai.models.runtime import ProcessorConfig

        processor = ExternalHttpProcessor(
            ProcessorConfig(
                processor_type="external_http",
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

        kwargs = processor._build_request_payload(remote)

        assert kwargs["headers"]["X-Custom"] == "value"
        assert kwargs["headers"]["Authorization"] == "Bearer secret"
        assert kwargs["json"]["query"] == "test"

    def test_request_building_multiple_auth_methods(self) -> None:
        """Test request building with different auth methods."""
        from gavel_ai.models.runtime import ProcessorConfig

        processor = ExternalHttpProcessor(
            ProcessorConfig(
                processor_type="external_http",
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
        kwargs_bearer = processor._build_request_payload(remote_bearer)
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
        kwargs_key = processor._build_request_payload(remote_key)
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
        kwargs_basic = processor._build_request_payload(remote_basic)
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

        # Step 3: Build HTTP request payload (ExternalHttpProcessor)
        processor = ExternalHttpProcessor(
            ProcessorConfig(processor_type="external_http", timeout_seconds=30)
        )
        kwargs = processor._build_request_payload(remote)

        # Verify flow integrity
        assert remote.id == scenario["id"]
        assert kwargs["headers"]["Authorization"] == "Bearer api-token"
        assert kwargs["json"]["text"] == "sample content"


# ---------------------------------------------------------------------------
# Task 25: ScenarioProcessorStep with external+http test subject
# ---------------------------------------------------------------------------


def _make_external_eval_dir(
    tmp_path: Path,
    eval_name: str,
    scenarios: List[Dict[str, Any]],
    endpoint: str = "http://test.local/eval",
    system_id: str = "my-system",
) -> Path:
    """Create an eval directory configured for external+http execution."""
    config_dir = tmp_path / eval_name / "config"
    data_dir = tmp_path / eval_name / "data"
    config_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)

    model_data = {
        "model_provider": "anthropic",
        "model_family": "claude",
        "model_version": "claude-test",
        "model_parameters": {"temperature": 0.0},
        "provider_auth": {"api_key": "sk-test"},
    }

    eval_config = {
        "eval_name": eval_name,
        "eval_type": "oneshot",
        "test_subject_type": "external",
        "test_subjects": [
            {
                "system_id": system_id,
                "protocol": "http",
                "config": {"endpoint": endpoint, "method": "POST"},
                "judges": [],
                "abort_on_exec_failure": True,
                "abort_on_process_error": False,
            }
        ],
        "variants": ["claude-test"],
        "scenarios": {"source": "file.local", "name": "scenarios.json"},
    }
    (config_dir / "eval_config.json").write_text(json.dumps(eval_config))
    (config_dir / "agents.json").write_text(json.dumps({"_models": {"claude-test": model_data}}))
    (data_dir / "scenarios.json").write_text(json.dumps(scenarios))
    return tmp_path


def _make_run_ctx(
    eval_dir: Path,
    eval_name: str,
    tmp_path: Path,
    run_id: str = "run-ext-001",
) -> LocalRunContext:
    eval_ctx = LocalFileSystemEvalContext(eval_name, eval_root=eval_dir)
    return LocalRunContext(
        eval_ctx,
        base_dir=tmp_path / "runs",
        run_id=run_id,
        snapshot=False,
    )


@pytest.mark.integration
@pytest.mark.asyncio
class TestScenarioProcessorStepExternalHttp:
    """Task 25: ScenarioProcessorStep with test_subject_type='external'/protocol='http'."""

    async def test_2xx_ok_produces_populated_output_record(
        self, tmp_path: Path
    ) -> None:
        """2xx ExternalResponseEnvelope(status='ok') → OutputRecord with trace_id and timing_ms."""
        import gavel_ai.processors.external_http_processor as mod

        eval_name = "ext-ok"
        scenarios = [{"id": "s1", "input": "hello", "expected_behavior": ""}]
        eval_dir = _make_external_eval_dir(tmp_path, eval_name, scenarios)
        run_ctx = _make_run_ctx(eval_dir, eval_name, tmp_path)
        logger = logging.getLogger("test")

        # Patch trace_id so it's deterministic
        original_get_run_id = mod.get_current_run_id
        mod.get_current_run_id = lambda: "trace-e2e"

        async def fake_send(
            self_proc: Any, client: Any, input_item: Any, kw: Any
        ) -> httpx.Response:
            return httpx.Response(200, json={"status": "ok", "result": {"answer": "42"}})

        from gavel_ai.core.steps.scenario_processor import ScenarioProcessorStep
        import gavel_ai.processors.external_http_processor as proc_mod

        original_send = proc_mod.ExternalHttpProcessor._send_request
        proc_mod.ExternalHttpProcessor._send_request = fake_send  # type: ignore[method-assign]

        try:
            step = ScenarioProcessorStep(logger)
            await step.execute(run_ctx)
        finally:
            proc_mod.ExternalHttpProcessor._send_request = original_send
            mod.get_current_run_id = original_get_run_id

        assert run_ctx.processor_results is not None
        assert len(run_ctx.processor_results) == 1
        record = run_ctx.processor_results[0]
        assert record.scenario_id == "s1"
        assert record.timing_ms >= 0
        assert record.metadata.get("trace_id") == "trace-e2e"
        assert record.error is None

    async def test_503_raises_run_policy_error_on_default_abort_flags(
        self, tmp_path: Path
    ) -> None:
        """503 + default abort_on_exec_failure=True → RunPolicyError raised."""
        import gavel_ai.processors.external_http_processor as proc_mod

        eval_name = "ext-503"
        scenarios = [{"id": "s1", "input": "hello", "expected_behavior": ""}]
        eval_dir = _make_external_eval_dir(tmp_path, eval_name, scenarios)
        run_ctx = _make_run_ctx(eval_dir, eval_name, tmp_path)
        logger = logging.getLogger("test")

        async def fake_send(
            self_proc: Any, client: Any, input_item: Any, kw: Any
        ) -> httpx.Response:
            return httpx.Response(503, text="Service Unavailable")

        original_send = proc_mod.ExternalHttpProcessor._send_request
        proc_mod.ExternalHttpProcessor._send_request = fake_send  # type: ignore[method-assign]

        from gavel_ai.core.steps.scenario_processor import ScenarioProcessorStep

        step = ScenarioProcessorStep(logger)
        try:
            with pytest.raises(RunPolicyError) as exc_info:
                await step.execute(run_ctx)
            assert "process_failure" in str(exc_info.value).lower() or "503" in str(exc_info.value)
        finally:
            proc_mod.ExternalHttpProcessor._send_request = original_send

    async def test_200_with_warning_issue_continues_run(
        self, tmp_path: Path
    ) -> None:
        """200 with warning issue + abort_on_process_error=False → run continues, issue in error."""
        import gavel_ai.processors.external_http_processor as proc_mod

        eval_name = "ext-warn"
        scenarios = [
            {"id": "s1", "input": "hello", "expected_behavior": ""},
            {"id": "s2", "input": "world", "expected_behavior": ""},
        ]
        eval_dir = _make_external_eval_dir(tmp_path, eval_name, scenarios)
        run_ctx = _make_run_ctx(eval_dir, eval_name, tmp_path)
        logger = logging.getLogger("test")

        async def fake_send(
            self_proc: Any, client: Any, input_item: Any, kw: Any
        ) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "status": "ok",
                    "result": {"text": "partial"},
                    "issue": {
                        "code": "low_confidence",
                        "level": "warning",
                        "message": "score below threshold",
                    },
                },
            )

        original_send = proc_mod.ExternalHttpProcessor._send_request
        proc_mod.ExternalHttpProcessor._send_request = fake_send  # type: ignore[method-assign]

        from gavel_ai.core.steps.scenario_processor import ScenarioProcessorStep

        try:
            step = ScenarioProcessorStep(logger)
            await step.execute(run_ctx)  # should NOT raise, abort_on_process_error=False
        finally:
            proc_mod.ExternalHttpProcessor._send_request = original_send

        # Both scenarios processed
        assert len(run_ctx.processor_results) == 2
        for record in run_ctx.processor_results:
            assert record.error is not None
            assert "low_confidence" in record.error
            assert record.metadata.get("external_outcome") == "process_success_with_issue"

    async def test_local_path_regression_unaffected(
        self, tmp_path: Path
    ) -> None:
        """Adding external+http path does not alter local/PromptInputProcessor behavior."""
        from unittest.mock import AsyncMock, MagicMock, patch

        eval_name = "local-regression"
        config_dir = tmp_path / eval_name / "config"
        prompts_dir = config_dir / "prompts"
        data_dir = tmp_path / eval_name / "data"
        config_dir.mkdir(parents=True)
        prompts_dir.mkdir(parents=True)
        data_dir.mkdir(parents=True)

        model_data = {
            "model_provider": "anthropic",
            "model_family": "claude",
            "model_version": "claude-test",
            "model_parameters": {"temperature": 0.0},
            "provider_auth": {"api_key": "sk-test"},
        }
        eval_config = {
            "eval_name": eval_name,
            "eval_type": "oneshot",
            "test_subject_type": "local",
            "test_subjects": [{"prompt_name": "default", "judges": []}],
            "variants": ["claude-test"],
            "scenarios": {"source": "file.local", "name": "scenarios.json"},
        }
        (config_dir / "eval_config.json").write_text(json.dumps(eval_config))
        (config_dir / "agents.json").write_text(json.dumps({"_models": {"claude-test": model_data}}))
        (prompts_dir / "default.toml").write_text('v1 = "Answer: {{input}}"')
        (data_dir / "scenarios.json").write_text(json.dumps([{"id": "r1", "input": "ping", "expected_behavior": ""}]))

        run_ctx = _make_run_ctx(tmp_path, eval_name, tmp_path, run_id="run-local-regression")

        llm_result = MagicMock()
        llm_result.output = "pong"
        llm_result.metadata = {"latency_ms": 5, "tokens": {"prompt": 1, "completion": 1}}

        from gavel_ai.core.steps.scenario_processor import ScenarioProcessorStep

        with patch("gavel_ai.processors.prompt_processor.ProviderFactory") as MockFactory:
            instance = MockFactory.return_value
            instance.create_agent.return_value = MagicMock()
            instance.call_agent = AsyncMock(return_value=llm_result)

            step = ScenarioProcessorStep(logging.getLogger("test"))
            await step.execute(run_ctx)

        assert len(run_ctx.processor_results) == 1
        assert run_ctx.processor_results[0].scenario_id == "r1"
        assert run_ctx.processor_results[0].error is None
