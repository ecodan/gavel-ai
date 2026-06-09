"""
Unit tests for ExternalHttpProcessor.

Tests:
- Building HTTP requests from RemoteSystemInput fields
- Authentication handling (bearer token, API key, basic auth)
- Unsupported method detection
- trace_id header injection
- Outcome classification (process_failure, process_success_with_issue) via MockTransport
- metadata["trace_id"] population in ProcessorResult
"""

import json
import logging
from typing import Any, Callable

import httpx
import pytest

from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.core.issue_classifier import ExternalOutcome
from gavel_ai.models.runtime import ProcessorConfig, RemoteSystemInput
from gavel_ai.processors.external_http_processor import ExternalHttpProcessor


def _make_processor(
    processor_config: ProcessorConfig,
    abort_on_exec_failure: bool = True,
    abort_on_process_error: bool = False,
    trace_header: str = "X-Gavel-Trace-Id",
) -> ExternalHttpProcessor:
    return ExternalHttpProcessor(
        processor_config,
        abort_on_exec_failure=abort_on_exec_failure,
        abort_on_process_error=abort_on_process_error,
        trace_header=trace_header,
    )


def _remote_input(endpoint: str = "http://test.local/eval") -> RemoteSystemInput:
    return RemoteSystemInput(
        id="s1",
        endpoint=endpoint,
        method="POST",
        headers={},
        body={"scenario_id": "s1", "input": "hello"},
    )


def _mock_transport(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


@pytest.fixture
def logger() -> logging.Logger:
    return logging.getLogger("test")


@pytest.fixture
def processor_config() -> ProcessorConfig:
    return ProcessorConfig(
        processor_type="external_http",
        parallelism=1,
        timeout_seconds=30,
        error_handling="fail_fast",
    )


@pytest.fixture
def processor(processor_config: ProcessorConfig) -> ExternalHttpProcessor:
    return ExternalHttpProcessor(processor_config)


@pytest.mark.unit
class TestExternalHttpProcessorRequestBuilding:
    """Test HTTP request payload construction."""

    def test_build_request_basic(self, processor: ExternalHttpProcessor) -> None:
        input_item = RemoteSystemInput(
            id="api-1",
            endpoint="https://api.example.com/analyze",
            method="POST",
            headers={"X-Custom": "header"},
            body={"text": "sample"},
        )

        kwargs = processor._build_request_payload(input_item)

        assert kwargs["headers"]["X-Custom"] == "header"
        assert kwargs["json"] == {"text": "sample"}

    def test_build_request_with_bearer_token(self, processor: ExternalHttpProcessor) -> None:
        input_item = RemoteSystemInput(
            id="api-2",
            endpoint="https://api.example.com",
            method="POST",
            headers={},
            body={},
            auth={"bearer_token": "secret-token-123"},
        )

        kwargs = processor._build_request_payload(input_item)

        assert "Authorization" in kwargs["headers"]
        assert kwargs["headers"]["Authorization"] == "Bearer secret-token-123"

    def test_build_request_with_api_key(self, processor: ExternalHttpProcessor) -> None:
        input_item = RemoteSystemInput(
            id="api-3",
            endpoint="https://api.example.com",
            method="POST",
            headers={},
            body={},
            auth={"api_key": "my-api-key-xyz"},
        )

        kwargs = processor._build_request_payload(input_item)

        assert "X-API-Key" in kwargs["headers"]
        assert kwargs["headers"]["X-API-Key"] == "my-api-key-xyz"

    def test_build_request_with_basic_auth(self, processor: ExternalHttpProcessor) -> None:
        input_item = RemoteSystemInput(
            id="api-4",
            endpoint="https://api.example.com",
            method="POST",
            headers={},
            body={},
            auth={"username": "user123", "password": "pass456"},
        )

        kwargs = processor._build_request_payload(input_item)

        assert "auth" in kwargs
        assert kwargs["auth"] == ("user123", "pass456")

    def test_build_request_empty_body(self, processor: ExternalHttpProcessor) -> None:
        input_item = RemoteSystemInput(
            id="api-5",
            endpoint="https://api.example.com",
            method="GET",
            headers={},
            body={},
        )

        kwargs = processor._build_request_payload(input_item)

        assert "json" not in kwargs

    def test_build_request_preserves_headers(self, processor: ExternalHttpProcessor) -> None:
        input_item = RemoteSystemInput(
            id="api-6",
            endpoint="https://api.example.com",
            method="POST",
            headers={"Content-Type": "application/json", "X-Custom": "value"},
            body={},
            auth={"bearer_token": "token"},
        )

        kwargs = processor._build_request_payload(input_item)

        assert kwargs["headers"]["Content-Type"] == "application/json"
        assert kwargs["headers"]["X-Custom"] == "value"
        assert kwargs["headers"]["Authorization"] == "Bearer token"

    def test_build_request_injects_trace_id_header(
        self, processor_config: ProcessorConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """trace_id from get_current_run_id is injected with the configured header name."""
        import gavel_ai.processors.external_http_processor as mod

        monkeypatch.setattr(mod, "get_current_run_id", lambda: "run-abc-123")
        proc = ExternalHttpProcessor(
            processor_config, trace_header="X-Custom-Trace"
        )
        input_item = RemoteSystemInput(
            id="trace-test",
            endpoint="https://api.example.com",
            method="POST",
            headers={},
            body={},
        )

        kwargs = proc._build_request_payload(input_item)

        assert kwargs["headers"]["X-Custom-Trace"] == "run-abc-123"

    def test_build_request_default_trace_header(
        self, processor_config: ProcessorConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Default trace header is X-Gavel-Trace-Id."""
        import gavel_ai.processors.external_http_processor as mod

        monkeypatch.setattr(mod, "get_current_run_id", lambda: "run-xyz")
        proc = ExternalHttpProcessor(processor_config)
        input_item = RemoteSystemInput(
            id="default-trace",
            endpoint="https://api.example.com",
            method="POST",
            headers={},
            body={},
        )

        kwargs = proc._build_request_payload(input_item)

        assert kwargs["headers"]["X-Gavel-Trace-Id"] == "run-xyz"

    def test_build_request_no_trace_header_when_run_id_none(
        self, processor_config: ProcessorConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When get_current_run_id returns None, no trace header is injected."""
        import gavel_ai.processors.external_http_processor as mod

        monkeypatch.setattr(mod, "get_current_run_id", lambda: None)
        proc = ExternalHttpProcessor(processor_config)
        input_item = RemoteSystemInput(
            id="no-trace",
            endpoint="https://api.example.com",
            method="POST",
            headers={},
            body={},
        )

        kwargs = proc._build_request_payload(input_item)

        assert "X-Gavel-Trace-Id" not in kwargs["headers"]


@pytest.mark.unit
class TestRemoteSystemInputValidation:
    """Test RemoteSystemInput creation and validation."""

    def test_create_remote_system_input_post(self) -> None:
        input_item = RemoteSystemInput(
            id="api-test",
            endpoint="https://api.example.com/analyze",
            method="POST",
            headers={"Content-Type": "application/json"},
            body={"query": "test data"},
        )

        assert input_item.id == "api-test"
        assert input_item.endpoint == "https://api.example.com/analyze"
        assert input_item.method == "POST"
        assert input_item.body["query"] == "test data"

    def test_create_remote_system_input_with_auth(self) -> None:
        input_item = RemoteSystemInput(
            id="api-secure",
            endpoint="https://api.example.com/secure",
            method="POST",
            headers={},
            body={"data": "value"},
            auth={"bearer_token": "secret"},
        )

        assert input_item.auth["bearer_token"] == "secret"  # type: ignore[index]

    def test_endpoint_required(self) -> None:
        with pytest.raises(Exception):
            RemoteSystemInput(
                id="api-no-endpoint",
                method="GET",
                headers={},
                body={},
            )  # type: ignore[call-arg]

    def test_method_required(self) -> None:
        with pytest.raises(Exception):
            RemoteSystemInput(
                id="api-no-method",
                endpoint="https://api.example.com",
                headers={},
                body={},
            )  # type: ignore[call-arg]


@pytest.mark.unit
class TestExternalHttpProcessorAbortFlags:
    """Test abort flag wiring and ExternalOutcome classification."""

    def test_default_abort_flags(self, processor: ExternalHttpProcessor) -> None:
        assert processor.abort_on_exec_failure is True
        assert processor.abort_on_process_error is False

    def test_custom_abort_flags(self, processor_config: ProcessorConfig) -> None:
        proc = ExternalHttpProcessor(
            processor_config,
            abort_on_exec_failure=False,
            abort_on_process_error=True,
        )
        assert proc.abort_on_exec_failure is False
        assert proc.abort_on_process_error is True


@pytest.mark.unit
class TestExternalHttpProcessorOutcomes:
    """Test outcome classification by patching the _send_request wire seam (no real network)."""

    @pytest.mark.asyncio
    async def test_http_4xx_returns_process_failure_error_tier(
        self, processor_config: ProcessorConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """HTTP 503 + abort_on_exec_failure=True → ProcessorResult.error set, tier ERROR."""
        import gavel_ai.processors.external_http_processor as mod

        monkeypatch.setattr(mod, "get_current_run_id", lambda: "run-test")

        proc = _make_processor(processor_config, abort_on_exec_failure=True)

        async def fake_send(client: Any, input_item: Any, kw: Any) -> httpx.Response:
            return httpx.Response(503, text="Service Unavailable")

        monkeypatch.setattr(proc, "_send_request", fake_send)

        result = await proc.process([_remote_input()])

        assert result.error is not None
        assert "503" in result.error
        assert result.metadata["external_outcome"] == ExternalOutcome.PROCESS_FAILURE.value
        assert result.metadata["external_tier"] == "ERROR"

    @pytest.mark.asyncio
    async def test_http_4xx_with_abort_false_returns_warning_tier(
        self, processor_config: ProcessorConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """HTTP 503 + abort_on_exec_failure=False → tier WARNING."""
        import gavel_ai.processors.external_http_processor as mod

        monkeypatch.setattr(mod, "get_current_run_id", lambda: "run-test")

        proc = _make_processor(processor_config, abort_on_exec_failure=False)

        async def fake_send(client: Any, input_item: Any, kw: Any) -> httpx.Response:
            return httpx.Response(503, text="Service Unavailable")

        monkeypatch.setattr(proc, "_send_request", fake_send)

        result = await proc.process([_remote_input()])

        assert result.error is not None
        assert result.metadata["external_tier"] == "WARNING"

    @pytest.mark.asyncio
    async def test_2xx_with_issue_returns_process_success_with_issue(
        self, processor_config: ProcessorConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """200 + envelope with issue + abort_on_process_error=False → WARNING tier."""
        import gavel_ai.processors.external_http_processor as mod

        monkeypatch.setattr(mod, "get_current_run_id", lambda: "run-test")

        envelope = {
            "status": "ok",
            "result": {"text": "partial"},
            "issue": {"code": "low_confidence", "level": "warning", "message": "score < 0.5"},
        }

        proc = _make_processor(processor_config, abort_on_process_error=False)

        async def fake_send(client: Any, input_item: Any, kw: Any) -> httpx.Response:
            return httpx.Response(200, json=envelope)

        monkeypatch.setattr(proc, "_send_request", fake_send)

        result = await proc.process([_remote_input()])

        assert result.error is not None
        assert result.metadata["external_outcome"] == ExternalOutcome.PROCESS_SUCCESS_WITH_ISSUE.value
        assert result.metadata["external_tier"] == "WARNING"
        assert "low_confidence" in result.error

    @pytest.mark.asyncio
    async def test_2xx_with_issue_and_abort_true_returns_error_tier(
        self, processor_config: ProcessorConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """200 + envelope with issue + abort_on_process_error=True → ERROR tier."""
        import gavel_ai.processors.external_http_processor as mod

        monkeypatch.setattr(mod, "get_current_run_id", lambda: "run-test")

        envelope = {
            "status": "ok",
            "issue": {"code": "validation_failed", "level": "error", "message": "bad output"},
        }

        proc = _make_processor(processor_config, abort_on_process_error=True)

        async def fake_send(client: Any, input_item: Any, kw: Any) -> httpx.Response:
            return httpx.Response(200, json=envelope)

        monkeypatch.setattr(proc, "_send_request", fake_send)

        result = await proc.process([_remote_input()])

        assert result.metadata["external_tier"] == "ERROR"

    @pytest.mark.asyncio
    async def test_2xx_ok_response_populates_trace_id_in_metadata(
        self, processor_config: ProcessorConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Successful 2xx response includes trace_id in metadata and header is injected."""
        import gavel_ai.processors.external_http_processor as mod

        monkeypatch.setattr(mod, "get_current_run_id", lambda: "trace-42")

        captured_headers: dict = {}

        async def fake_send(client: Any, input_item: Any, kw: Any) -> httpx.Response:
            captured_headers.update(kw.get("headers", {}))
            return httpx.Response(200, json={"status": "ok", "result": {"answer": "yes"}})

        proc = _make_processor(processor_config)
        monkeypatch.setattr(proc, "_send_request", fake_send)

        result = await proc.process([_remote_input()])

        assert result.error is None
        assert result.metadata["trace_id"] == "trace-42"
        assert captured_headers.get("X-Gavel-Trace-Id") == "trace-42"
