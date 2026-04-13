"""
Unit tests for ClosedBoxInputProcessor Phase 4.

Tests:
- Building HTTP requests from RemoteSystemInput fields
- Authentication handling (bearer token, API key, basic auth)
- Unsupported method detection
"""

import logging

import pytest

from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.models.runtime import ProcessorConfig, RemoteSystemInput
from gavel_ai.processors.closedbox_processor import ClosedBoxInputProcessor


@pytest.fixture
def logger() -> logging.Logger:
    """Provide a logger for testing."""
    return logging.getLogger("test")


@pytest.fixture
def processor_config() -> ProcessorConfig:
    """Provide a ProcessorConfig for testing."""
    return ProcessorConfig(
        processor_type="closedbox_input",
        parallelism=1,
        timeout_seconds=30,
        error_handling="fail_fast",
    )


@pytest.fixture
def processor(processor_config: ProcessorConfig) -> ClosedBoxInputProcessor:
    """Provide a ClosedBoxInputProcessor instance."""
    return ClosedBoxInputProcessor(processor_config)


@pytest.mark.unit
class TestClosedBoxInputProcessorRequestBuilding:
    """Test HTTP request building functionality."""

    def test_build_request_basic(self, processor: ClosedBoxInputProcessor) -> None:
        """Test building a basic request without auth."""
        input_item = RemoteSystemInput(
            id="api-1",
            endpoint="https://api.example.com/analyze",
            method="POST",
            headers={"X-Custom": "header"},
            body={"text": "sample"},
        )

        kwargs = processor._build_request_kwargs(input_item)

        assert kwargs["headers"]["X-Custom"] == "header"
        assert kwargs["json"] == {"text": "sample"}

    def test_build_request_with_bearer_token(
        self, processor: ClosedBoxInputProcessor
    ) -> None:
        """Test building request with bearer token auth."""
        input_item = RemoteSystemInput(
            id="api-2",
            endpoint="https://api.example.com",
            method="POST",
            headers={},
            body={},
            auth={"bearer_token": "secret-token-123"},
        )

        kwargs = processor._build_request_kwargs(input_item)

        assert "Authorization" in kwargs["headers"]
        assert kwargs["headers"]["Authorization"] == "Bearer secret-token-123"

    def test_build_request_with_api_key(
        self, processor: ClosedBoxInputProcessor
    ) -> None:
        """Test building request with API key auth."""
        input_item = RemoteSystemInput(
            id="api-3",
            endpoint="https://api.example.com",
            method="POST",
            headers={},
            body={},
            auth={"api_key": "my-api-key-xyz"},
        )

        kwargs = processor._build_request_kwargs(input_item)

        assert "X-API-Key" in kwargs["headers"]
        assert kwargs["headers"]["X-API-Key"] == "my-api-key-xyz"

    def test_build_request_with_basic_auth(
        self, processor: ClosedBoxInputProcessor
    ) -> None:
        """Test building request with basic auth (username/password)."""
        input_item = RemoteSystemInput(
            id="api-4",
            endpoint="https://api.example.com",
            method="POST",
            headers={},
            body={},
            auth={"username": "user123", "password": "pass456"},
        )

        kwargs = processor._build_request_kwargs(input_item)

        assert "auth" in kwargs
        assert kwargs["auth"] == ("user123", "pass456")

    def test_build_request_empty_body(
        self, processor: ClosedBoxInputProcessor
    ) -> None:
        """Test that empty body is not included in kwargs."""
        input_item = RemoteSystemInput(
            id="api-5",
            endpoint="https://api.example.com",
            method="GET",
            headers={},
            body={},
        )

        kwargs = processor._build_request_kwargs(input_item)

        assert "json" not in kwargs
        assert kwargs["headers"] == {}

    def test_build_request_preserves_headers(
        self, processor: ClosedBoxInputProcessor
    ) -> None:
        """Test that existing headers are preserved when adding auth."""
        input_item = RemoteSystemInput(
            id="api-6",
            endpoint="https://api.example.com",
            method="POST",
            headers={"Content-Type": "application/json", "X-Custom": "value"},
            body={},
            auth={"bearer_token": "token"},
        )

        kwargs = processor._build_request_kwargs(input_item)

        assert kwargs["headers"]["Content-Type"] == "application/json"
        assert kwargs["headers"]["X-Custom"] == "value"
        assert kwargs["headers"]["Authorization"] == "Bearer token"


@pytest.mark.unit
class TestRemoteSystemInputValidation:
    """Test RemoteSystemInput creation and validation."""

    def test_create_remote_system_input_post(self) -> None:
        """Test creating RemoteSystemInput for POST request."""
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
        """Test creating RemoteSystemInput with authentication."""
        input_item = RemoteSystemInput(
            id="api-secure",
            endpoint="https://api.example.com/secure",
            method="POST",
            headers={},
            body={"data": "value"},
            auth={"bearer_token": "secret"},
        )

        assert input_item.auth["bearer_token"] == "secret"

    def test_endpoint_required(self) -> None:
        """Test that endpoint is required."""
        with pytest.raises(Exception):
            RemoteSystemInput(
                id="api-no-endpoint",
                method="GET",
                headers={},
                body={},
            )

    def test_method_required(self) -> None:
        """Test that method is required."""
        with pytest.raises(Exception):
            RemoteSystemInput(
                id="api-no-method",
                endpoint="https://api.example.com",
                headers={},
                body={},
            )
