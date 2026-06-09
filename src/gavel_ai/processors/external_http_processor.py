"""
ExternalHttpProcessor: sends HTTP requests to external evaluation systems.

Implements the three-seam ADR-10 structure:
  - _build_request_payload : outbound payload construction
  - _send_request          : wire transport (httpx)
  - _parse_response        : inbound response interpretation → ExternalResponseEnvelope

Outcomes are classified via classify_external_outcome and surfaced through
ProcessorResult.error / metadata["external_tier"] so the caller's
should_halt path does not need to re-derive the tier.
"""

import json
import time
from typing import Any, Dict, List, Optional, Tuple, cast

import httpx

from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.core.issue_classifier import (
    ExternalOutcome,
    classify_external_outcome,
)
from gavel_ai.models.runtime import (
    ExternalIssue,
    ExternalResponseEnvelope,
    ProcessorConfig,
    ProcessorResult,
    RemoteSystemInput,
)
from gavel_ai.processors.base import InputProcessor
from gavel_ai.telemetry import get_current_run_id, get_tracer

# Default header name used to forward the Gavel run trace_id to external systems.
DEFAULT_TRACE_HEADER: str = "X-Gavel-Trace-Id"


class ExternalHttpProcessor(InputProcessor):
    """
    Process inputs against deployed HTTP endpoints (external systems).

    Accepts RemoteSystemInput with endpoint, method, headers, body, auth.
    Classifies outcomes via classify_external_outcome and propagates them
    through ProcessorResult rather than raising exceptions, so the pipeline's
    error_policy.should_halt path controls halting behaviour.
    """

    def __init__(self, config: ProcessorConfig, **kwargs: Any) -> None:
        """
        Args:
            config: ProcessorConfig with timeout/parallelism settings.
            abort_on_exec_failure: Halt on PROCESS_FAILURE (default True).
            abort_on_process_error: Halt on PROCESS_SUCCESS_WITH_ISSUE (default False).
            trace_header: HTTP header name for outbound trace_id injection
                          (default: X-Gavel-Trace-Id).
            adapter: Outcome-classifier adapter key (default: "gavel").
        """
        super().__init__(config)
        self.tracer = get_tracer(__name__)
        self.abort_on_exec_failure: bool = bool(kwargs.get("abort_on_exec_failure", True))
        self.abort_on_process_error: bool = bool(kwargs.get("abort_on_process_error", False))
        self.trace_header: str = str(kwargs.get("trace_header", DEFAULT_TRACE_HEADER))
        self.adapter: str = str(kwargs.get("adapter", "gavel"))

    # ------------------------------------------------------------------
    # Seam 1: outbound payload construction
    # ------------------------------------------------------------------

    def _build_request_payload(self, input_item: RemoteSystemInput) -> Dict[str, Any]:
        """Build httpx request kwargs from RemoteSystemInput, injecting trace_id header."""
        headers: Dict[str, str] = dict(input_item.headers or {})

        trace_id = self._get_trace_id()
        if trace_id:
            headers[self.trace_header] = trace_id

        kwargs: Dict[str, Any] = {"headers": headers}

        if input_item.body:
            kwargs["json"] = input_item.body

        if input_item.auth:
            if "bearer_token" in input_item.auth:
                kwargs["headers"]["Authorization"] = f"Bearer {input_item.auth['bearer_token']}"
            elif "api_key" in input_item.auth:
                kwargs["headers"]["X-API-Key"] = input_item.auth["api_key"]
            elif "username" in input_item.auth and "password" in input_item.auth:
                kwargs["auth"] = (input_item.auth["username"], input_item.auth["password"])

        return kwargs

    def _get_trace_id(self) -> Optional[str]:
        """Return current run trace_id for header injection."""
        return get_current_run_id()

    # ------------------------------------------------------------------
    # Seam 2: wire transport
    # ------------------------------------------------------------------

    async def _send_request(
        self,
        client: httpx.AsyncClient,
        input_item: RemoteSystemInput,
        payload_kwargs: Dict[str, Any],
    ) -> httpx.Response:
        """Dispatch the HTTP request over the wire and return the raw response."""
        method = input_item.method.upper()
        allowed = {"GET", "POST", "PUT", "DELETE", "PATCH"}
        if method not in allowed:
            raise ProcessorError(
                f"Unsupported HTTP method '{method}' - "
                "Use GET, POST, PUT, DELETE, or PATCH"
            )
        send = getattr(client, method.lower())
        return cast(httpx.Response, await send(input_item.endpoint, **payload_kwargs))

    # ------------------------------------------------------------------
    # Seam 3: inbound response parsing
    # ------------------------------------------------------------------

    def _parse_response(
        self, response: httpx.Response
    ) -> Tuple[str, Optional[ExternalOutcome], Optional[ExternalIssue]]:
        """
        Interpret a 2xx HTTP response body.

        Returns (output_text, outcome, issue):
          - outcome None  → PROCESS_SUCCESS (no error surfaced)
          - outcome PROCESS_SUCCESS_WITH_ISSUE → 2xx with issue envelope
          - outcome PROCESS_FAILURE → envelope status == "error"
        """
        try:
            body = response.json()
        except (json.JSONDecodeError, ValueError):
            return response.text, None, None

        try:
            envelope = ExternalResponseEnvelope.model_validate(body)
        except Exception:
            output = body.get("response", response.text) if isinstance(body, dict) else response.text
            return str(output), None, None

        if envelope.status == "error":
            issue_text = (
                f"{envelope.issue.code}: {envelope.issue.message}"
                if envelope.issue
                else "external system reported status=error"
            )
            return "", ExternalOutcome.PROCESS_FAILURE, envelope.issue

        if envelope.issue is not None:
            result_text = json.dumps(envelope.result) if envelope.result else ""
            return result_text, ExternalOutcome.PROCESS_SUCCESS_WITH_ISSUE, envelope.issue

        result_text = json.dumps(envelope.result) if envelope.result else response.text
        return result_text, None, None

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    async def process(self, inputs: List[RemoteSystemInput]) -> ProcessorResult:  # type: ignore[override]
        """
        Execute batch of RemoteSystemInput via HTTP.

        Returns ProcessorResult with error/metadata["external_tier"] populated for
        non-OK outcomes rather than raising, so the caller's should_halt path applies.
        """
        all_outputs: List[str] = []
        aggregated_metadata: Dict[str, Any] = {
            "total_latency_ms": 0,
            "input_count": len(inputs),
            "endpoints": [inp.endpoint for inp in inputs],
            "trace_id": self._get_trace_id() or "",
        }
        last_status_code: int = 0

        async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
            for input_item in inputs:
                start_time = time.time()

                try:
                    payload_kwargs = self._build_request_payload(input_item)
                    response = await self._send_request(client, input_item, payload_kwargs)
                    duration_ms = int((time.time() - start_time) * 1000)
                    aggregated_metadata["total_latency_ms"] += duration_ms
                    last_status_code = response.status_code

                    if response.status_code >= 400:
                        tier = classify_external_outcome(
                            ExternalOutcome.PROCESS_FAILURE,
                            self.abort_on_exec_failure,
                            self.abort_on_process_error,
                            self.adapter,
                        )
                        aggregated_metadata.update({
                            "status_code": last_status_code,
                            "external_outcome": ExternalOutcome.PROCESS_FAILURE.value,
                            "external_tier": tier,
                        })
                        return ProcessorResult(
                            output="",
                            error=(
                                f"HTTP {response.status_code} error from {input_item.endpoint} - "
                                "Check endpoint health and request format"
                            ),
                            metadata=aggregated_metadata,
                        )

                    output, outcome, issue = self._parse_response(response)

                    if outcome is not None:
                        tier = classify_external_outcome(
                            outcome,
                            self.abort_on_exec_failure,
                            self.abort_on_process_error,
                            self.adapter,
                        )
                        if outcome is ExternalOutcome.PROCESS_SUCCESS_WITH_ISSUE and issue:
                            error_msg = (
                                f"External system issue [{issue.level}] {issue.code}: "
                                f"{issue.message}"
                            )
                        else:
                            error_msg = (
                                f"External system process failure at {input_item.endpoint}: "
                                + (
                                    f"{issue.code}: {issue.message}"
                                    if issue
                                    else "status=error with no issue detail"
                                )
                            )
                        aggregated_metadata.update({
                            "status_code": last_status_code,
                            "external_outcome": outcome.value,
                            "external_tier": tier,
                        })
                        return ProcessorResult(
                            output=output,
                            error=error_msg,
                            metadata=aggregated_metadata,
                        )

                    all_outputs.append(str(output))

                except httpx.ConnectError as exc:
                    duration_ms = int((time.time() - start_time) * 1000)
                    aggregated_metadata["total_latency_ms"] += duration_ms
                    tier = classify_external_outcome(
                        ExternalOutcome.PROCESS_FAILURE,
                        self.abort_on_exec_failure,
                        self.abort_on_process_error,
                        self.adapter,
                    )
                    aggregated_metadata.update({
                        "external_outcome": ExternalOutcome.PROCESS_FAILURE.value,
                        "external_tier": tier,
                    })
                    return ProcessorResult(
                        output="",
                        error=(
                            f"HTTP endpoint unavailable at {input_item.endpoint} - "
                            "Check endpoint is running and URL is correct"
                        ),
                        metadata=aggregated_metadata,
                    )
                except httpx.TimeoutException as exc:
                    duration_ms = int((time.time() - start_time) * 1000)
                    aggregated_metadata["total_latency_ms"] += duration_ms
                    tier = classify_external_outcome(
                        ExternalOutcome.PROCESS_FAILURE,
                        self.abort_on_exec_failure,
                        self.abort_on_process_error,
                        self.adapter,
                    )
                    aggregated_metadata.update({
                        "external_outcome": ExternalOutcome.PROCESS_FAILURE.value,
                        "external_tier": tier,
                    })
                    return ProcessorResult(
                        output="",
                        error=(
                            f"HTTP request timed out after {self.config.timeout_seconds}s - "
                            "Increase timeout_seconds or check endpoint performance"
                        ),
                        metadata=aggregated_metadata,
                    )
                except ProcessorError:
                    raise
                except httpx.RequestError as exc:
                    raise ProcessorError(
                        f"Failed to process input {input_item.id}: {exc} - "
                        "Check endpoint response format and network connectivity"
                    ) from exc

        aggregated_metadata["status_code"] = last_status_code
        combined_output = (
            "\n\n".join(all_outputs) if len(all_outputs) > 1 else (all_outputs[0] if all_outputs else "")
        )
        return ProcessorResult(output=combined_output, metadata=aggregated_metadata)
