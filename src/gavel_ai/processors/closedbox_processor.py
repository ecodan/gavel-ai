"""
ClosedBoxInputProcessor implementation for HTTP endpoint evaluation.

Processes inputs by sending them to deployed in-situ systems via HTTP.
"""

import time
from typing import Any, Dict, List, Optional

import httpx

from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.core.models import Input, ProcessorConfig, ProcessorResult
from gavel_ai.processors.base import InputProcessor
from gavel_ai.telemetry import get_current_run_id, get_tracer


class ClosedBoxInputProcessor(InputProcessor):
    """
    Process inputs against deployed HTTP endpoints (in-situ systems).

    Per Architecture Decision 3: Config-driven design with per-processor batching.
    Enables testing of production systems without accessing internal models.
    """

    def __init__(
        self,
        config: ProcessorConfig,
        endpoint_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize processor with HTTP endpoint configuration.

        Args:
            config: ProcessorConfig instance with processor behavioral rules
            endpoint_url: URL of the HTTP endpoint to test
            headers: Optional custom headers to send with requests

        Raises:
            ProcessorError: If endpoint_url is not provided
        """
        super().__init__(config)
        self.tracer = get_tracer(__name__)

        if not endpoint_url:
            raise ProcessorError(
                "endpoint_url required for ClosedBoxInputProcessor - "
                "Provide endpoint_url parameter when creating processor"
            )

        self.endpoint_url = endpoint_url
        self.headers = headers or {}

    async def process(self, inputs: List[Input]) -> ProcessorResult:
        """
        Execute processor against batch of inputs via HTTP.

        Args:
            inputs: List of Input instances to process

        Returns:
            ProcessorResult with output, metadata, and optional error

        Raises:
            ProcessorError: On execution failures
        """
        all_outputs: List[str] = []
        aggregated_metadata: Dict[str, Any] = {
            "total_latency_ms": 0,
            "input_count": len(inputs),
            "endpoint_url": self.endpoint_url,
        }
        last_status_code = 0

        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            for input_item in inputs:
                start_time = time.time()

                try:
                    # Prepare request payload
                    payload = {
                        "id": input_item.id,
                        "input": input_item.text,
                        "metadata": input_item.metadata,
                    }

                    # Make HTTP POST request
                    response = await client.post(
                        self.endpoint_url,
                        json=payload,
                        headers=self.headers,
                    )

                    duration_ms = int((time.time() - start_time) * 1000)
                    last_status_code = response.status_code

                    # Check for HTTP errors
                    if response.status_code >= 400:
                        raise ProcessorError(
                            f"HTTP {response.status_code} error from endpoint - "
                            f"Check endpoint health and request format"
                        )

                    # Extract response
                    try:
                        response_data = response.json()
                        output = response_data.get("response", response.text)
                    except Exception:
                        # If not JSON, use raw text
                        output = response.text

                    all_outputs.append(str(output))

                    # Aggregate metadata
                    aggregated_metadata["total_latency_ms"] += duration_ms

                except httpx.ConnectError as e:
                    raise ProcessorError(
                        f"HTTP endpoint unavailable at {self.endpoint_url} - "
                        f"Check endpoint is running and URL is correct"
                    ) from e
                except httpx.TimeoutException as e:
                    raise ProcessorError(
                        f"HTTP request timed out after {self.config.timeout_seconds}s - "
                        f"Increase timeout_seconds or check endpoint performance"
                    ) from e
                except ProcessorError:
                    raise
                except Exception as e:
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
