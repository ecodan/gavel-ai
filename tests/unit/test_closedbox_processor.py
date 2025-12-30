"""
Unit tests for ClosedBoxInputProcessor.

Tests HTTP endpoint evaluation for in-situ systems.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.core.models import Input, ProcessorConfig, ProcessorResult
from gavel_ai.processors.closedbox_processor import ClosedBoxInputProcessor


class TestClosedBoxInputProcessor:
    """Test ClosedBoxInputProcessor initialization and configuration."""

    def test_processor_initialization(self):
        """Test processor can be initialized with endpoint URL."""
        config = ProcessorConfig(
            processor_type="closedbox_input",
        )
        processor = ClosedBoxInputProcessor(config, endpoint_url="http://localhost:8000/api")

        assert processor is not None
        assert processor.endpoint_url == "http://localhost:8000/api"

    def test_processor_requires_endpoint_url(self):
        """Test processor raises error if endpoint_url not provided."""
        config = ProcessorConfig(processor_type="closedbox_input")

        with pytest.raises(ProcessorError, match="endpoint_url required"):
            ClosedBoxInputProcessor(config)


class TestHTTPExecution:
    """Test HTTP request execution."""

    @pytest.mark.asyncio
    async def test_process_makes_http_request(self):
        """Test process() makes HTTP POST request to endpoint."""
        config = ProcessorConfig(processor_type="closedbox_input")
        processor = ClosedBoxInputProcessor(config, endpoint_url="http://test.com/api")

        inputs = [Input(id="1", text="test query", metadata={})]

        with patch("httpx.AsyncClient") as MockClient:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "Test response from endpoint"
            mock_response.json.return_value = {"response": "Test response from endpoint"}

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__.return_value = mock_client_instance

            result = await processor.process(inputs)

            assert isinstance(result, ProcessorResult)
            assert "Test response" in result.output
            mock_client_instance.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_extracts_metadata(self):
        """Test metadata extraction from HTTP response."""
        config = ProcessorConfig(processor_type="closedbox_input")
        processor = ClosedBoxInputProcessor(config, endpoint_url="http://test.com/api")

        inputs = [Input(id="1", text="query", metadata={})]

        with patch("httpx.AsyncClient") as MockClient:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "Response"
            mock_response.json.return_value = {"response": "Response"}

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__.return_value = mock_client_instance

            result = await processor.process(inputs)

            assert "status_code" in result.metadata
            assert result.metadata["status_code"] == 200
            assert "total_latency_ms" in result.metadata

    @pytest.mark.asyncio
    async def test_process_handles_endpoint_unavailable(self):
        """Test error handling when endpoint is unavailable."""
        config = ProcessorConfig(processor_type="closedbox_input")
        processor = ClosedBoxInputProcessor(config, endpoint_url="http://test.com/api")

        inputs = [Input(id="1", text="query", metadata={})]

        import httpx
        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            MockClient.return_value.__aenter__.return_value = mock_client_instance

            with pytest.raises(ProcessorError, match="endpoint unavailable"):
                await processor.process(inputs)

    @pytest.mark.asyncio
    async def test_process_handles_http_error_status(self):
        """Test handling of HTTP error status codes."""
        config = ProcessorConfig(processor_type="closedbox_input")
        processor = ClosedBoxInputProcessor(config, endpoint_url="http://test.com/api")

        inputs = [Input(id="1", text="query", metadata={})]

        with patch("httpx.AsyncClient") as MockClient:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__.return_value = mock_client_instance

            with pytest.raises(ProcessorError, match="HTTP 500"):
                await processor.process(inputs)

    @pytest.mark.asyncio
    async def test_process_with_custom_headers(self):
        """Test sending custom headers with request."""
        config = ProcessorConfig(processor_type="closedbox_input")
        headers = {"Authorization": "Bearer token123", "X-Custom": "value"}
        processor = ClosedBoxInputProcessor(
            config, endpoint_url="http://test.com/api", headers=headers
        )

        inputs = [Input(id="1", text="query", metadata={})]

        with patch("httpx.AsyncClient") as MockClient:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "Response"
            mock_response.json.return_value = {"response": "Response"}

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__.return_value = mock_client_instance

            await processor.process(inputs)

            # Verify headers were passed
            call_args = mock_client_instance.post.call_args
            assert call_args.kwargs.get("headers") == headers

    @pytest.mark.asyncio
    async def test_process_batch_of_inputs(self):
        """Test processing multiple inputs."""
        config = ProcessorConfig(processor_type="closedbox_input")
        processor = ClosedBoxInputProcessor(config, endpoint_url="http://test.com/api")

        inputs = [
            Input(id="1", text="query1", metadata={}),
            Input(id="2", text="query2", metadata={}),
        ]

        with patch("httpx.AsyncClient") as MockClient:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "Response"
            mock_response.json.return_value = {"response": "Response"}

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__.return_value = mock_client_instance

            result = await processor.process(inputs)

            assert isinstance(result, ProcessorResult)
            # Should make 2 requests (one per input)
            assert mock_client_instance.post.call_count == 2
