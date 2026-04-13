"""
ClosedBoxInputProcessor implementation for HTTP endpoint evaluation.

Phase 4: Updated to accept RemoteSystemInput with endpoint, method, body, auth.
Processes inputs by sending them to deployed in-situ systems via HTTP.
"""

import json
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.models.runtime import ProcessorConfig, ProcessorResult, RemoteSystemInput
from gavel_ai.processors.base import InputProcessor
from gavel_ai.telemetry import get_tracer


class ClosedBoxInputProcessor(InputProcessor):
    """
    Process inputs against deployed HTTP endpoints (in-situ systems).

    Phase 4: Accepts RemoteSystemInput with per-input endpoint, method, headers, body, auth.
    Per Architecture Decision 3: Config-driven design with per-processor batching.
    Enables testing of production systems without accessing internal models.
    """

    def __init__(self, config: ProcessorConfig, **kwargs: Any) -> None:
        """
        Initialize processor with HTTP endpoint configuration.

        Args:
            config: ProcessorConfig instance with processor behavioral rules
            **kwargs: Ignored (for compatibility with ScenarioProcessorStep)
        """
        super().__init__(config)
        self.tracer = get_tracer(__name__)

    def _build_request_kwargs(self, input_item: RemoteSystemInput) -> Dict[str, Any]:
        """
        Build httpx request kwargs from RemoteSystemInput.

        Args:
            input_item: RemoteSystemInput with endpoint, method, headers, body, auth

        Returns:
            Dict of kwargs for httpx client request method
        """
        kwargs: Dict[str, Any] = {
            "headers": input_item.headers or {},
        }

        # Add body if present
        if input_item.body:
            kwargs["json"] = input_item.body

        # Add authentication if present
        if input_item.auth:
            if "bearer_token" in input_item.auth:
                auth_header = f"Bearer {input_item.auth['bearer_token']}"
                kwargs["headers"]["Authorization"] = auth_header
            elif "api_key" in input_item.auth:
                kwargs["headers"]["X-API-Key"] = input_item.auth["api_key"]
            elif "username" in input_item.auth and "password" in input_item.auth:
                kwargs["auth"] = (input_item.auth["username"], input_item.auth["password"])

        return kwargs

    async def process(self, inputs: List[RemoteSystemInput]) -> ProcessorResult:
        """
        Execute processor against batch of RemoteSystemInput via HTTP.

        Phase 4: Accepts RemoteSystemInput with endpoint, method, headers, body, auth.
        Builds HTTP requests from input fields and sends to remote endpoints.

        Args:
            inputs: List of RemoteSystemInput instances with API call details

        Returns:
            ProcessorResult with output, metadata, and optional error

        Raises:
            ProcessorError: On execution failures
        """
        all_outputs: List[str] = []
        aggregated_metadata: Dict[str, Any] = {
            "total_latency_ms": 0,
            "input_count": len(inputs),
            "endpoints": [inp.endpoint for inp in inputs],
        }
        last_status_code = 0

        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            for input_item in inputs:
                start_time = time.time()

                try:
                    # Build request kwargs from RemoteSystemInput
                    request_kwargs = self._build_request_kwargs(input_item)

                    # Make HTTP request using the method from input
                    method = input_item.method.upper()
                    if method == "GET":
                        response = await client.get(input_item.endpoint, **request_kwargs)
                    elif method == "POST":
                        response = await client.post(input_item.endpoint, **request_kwargs)
                    elif method == "PUT":
                        response = await client.put(input_item.endpoint, **request_kwargs)
                    elif method == "DELETE":
                        response = await client.delete(input_item.endpoint, **request_kwargs)
                    elif method == "PATCH":
                        response = await client.patch(input_item.endpoint, **request_kwargs)
                    else:
                        raise ProcessorError(
                            f"Unsupported HTTP method '{method}' - "
                            f"Use GET, POST, PUT, DELETE, or PATCH"
                        )

                    duration_ms = int((time.time() - start_time) * 1000)
                    last_status_code = response.status_code

                    # Check for HTTP errors
                    if response.status_code >= 400:
                        raise ProcessorError(
                            f"HTTP {response.status_code} error from {input_item.endpoint} - "
                            f"Check endpoint health and request format"
                        )

                    # Extract response
                    try:
                        response_data = response.json()
                        output = response_data.get("response", response.text)
                    except json.JSONDecodeError:
                        # If not JSON, use raw text
                        output = response.text

                    all_outputs.append(str(output))

                    # Aggregate metadata
                    aggregated_metadata["total_latency_ms"] += duration_ms

                except httpx.ConnectError as e:
                    raise ProcessorError(
                        f"HTTP endpoint unavailable at {input_item.endpoint} - "
                        f"Check endpoint is running and URL is correct"
                    ) from e
                except httpx.TimeoutException as e:
                    raise ProcessorError(
                        f"HTTP request timed out after {self.config.timeout_seconds}s - "
                        f"Increase timeout_seconds or check endpoint performance"
                    ) from e
                except ProcessorError:
                    raise
                except httpx.RequestError as e:
                    raise ProcessorError(
                        f"Failed to process input {input_item.id}: {e} - "
                        f"Check endpoint response format and network connectivity"
                    ) from e

        # Add status code to metadata
        aggregated_metadata["status_code"] = last_status_code

        # Combine all outputs
        combined_output = "\n\n".join(all_outputs) if len(all_outputs) > 1 else all_outputs[0]

        return ProcessorResult(
            output=combined_output,
            metadata=aggregated_metadata,
        )
