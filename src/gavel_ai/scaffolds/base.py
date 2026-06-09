"""
Base mixin for external system-under-test scaffold classes.

This module is intentionally isolated from gavel_ai.core.* — it is shipped
as a standalone helper for external system authors and must NOT import from
any gavel_ai.core module.

Design (ADR-6):
- `_BaseSystemUnderTest` provides parse/validate → handle → assemble lifecycle.
- Subclasses implement exactly one method: ``handle(request) -> result``.
- Structured log line with ``trace_id`` is emitted for every ``handle`` invocation.
- Malformed requests produce a clear error referencing ``schema-external-runner.md``.
"""

import logging
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import ValidationError

from gavel_ai.models.runtime import (
    ExternalIssue,
    ExternalResponseEnvelope,
    ExternalTaskRequest,
)

# ── Logger ──────────────────────────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)s> %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_logger = logging.getLogger("gavel-ai.scaffolds")
if not _logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)

# Schema reference embedded in user-visible validation error messages (ADR-7).
_SCHEMA_REF = "docs/specs/schema-external-runner.md"


class ScaffoldValidationError(ValueError):
    """Raised when an inbound request fails schema validation.

    The message always names the missing/mismatched field and the schema doc
    path so external authors can quickly locate the fix.
    """


class _BaseSystemUnderTest(ABC):
    """
    Abstract base providing request lifecycle for external SUT scaffolds.

    Subclasses must implement ``handle(request: ExternalTaskRequest) -> result``.

    Usage::

        class MySystem(_BaseSystemUnderTest):
            def handle(self, request: ExternalTaskRequest) -> Dict[str, Any]:
                # call your system under test here
                return {"output": "response text"}
    """

    # ── Public entry-point ───────────────────────────────────────────────────

    def process(self, raw: Dict[str, Any]) -> ExternalResponseEnvelope:
        """Full lifecycle: parse → handle → assemble.

        Args:
            raw: Inbound payload dict (from HTTP POST body or script request.json).

        Returns:
            ExternalResponseEnvelope with status, result, metadata, issue, trace_id.
        """
        request = self._parse_and_validate(raw)
        self._emit_span(request)
        try:
            result = self.handle(request)
        except Exception as exc:
            return self._assemble_response(
                request=request,
                result=None,
                issue=ExternalIssue(
                    code="handle_error",
                    level="error",
                    message=str(exc),
                ),
                error=True,
            )

        # If handle returned an ExternalIssue, surface it with status=ok.
        issue: Optional[ExternalIssue] = None
        if isinstance(result, ExternalIssue):
            issue = result
            result = None

        return self._assemble_response(request=request, result=result, issue=issue, error=False)

    # ── Abstract method ──────────────────────────────────────────────────────

    @abstractmethod
    def handle(self, request: ExternalTaskRequest) -> Any:
        """Process a validated request and return a result dict or ExternalIssue.

        Args:
            request: Validated ``ExternalTaskRequest`` instance.

        Returns:
            A ``dict`` payload to include in ``result``, or an ``ExternalIssue``
            to surface a warning/error with ``status: "ok"``.

        Raises:
            Any exception → assembled response will have ``status: "error"``.
        """

    # ── Protected helpers ────────────────────────────────────────────────────

    def _parse_and_validate(self, raw: Dict[str, Any]) -> ExternalTaskRequest:
        """Parse and validate the inbound payload against ExternalTaskRequest schema.

        Raises:
            ScaffoldValidationError: if validation fails, with a message that names
                the missing/mismatched field and the schema doc path.
        """
        try:
            return ExternalTaskRequest.model_validate(raw)
        except ValidationError as exc:
            # Build a human-readable summary of every error.
            field_msgs = []
            for err in exc.errors():
                loc = ".".join(str(p) for p in err["loc"]) if err["loc"] else "<root>"
                field_msgs.append(f"  field '{loc}': {err['msg']}")
            detail = "\n".join(field_msgs)
            raise ScaffoldValidationError(
                f"Request failed schema validation (see {_SCHEMA_REF}):\n{detail}"
            ) from exc

    def _emit_span(self, request: ExternalTaskRequest) -> None:
        """Emit a structured log line carrying trace_id for every handle invocation."""
        _logger.info(
            "scaffold_handle_invocation scenario_id=%s trace_id=%s",
            request.scenario_id,
            request.trace_id,
        )

    def _assemble_response(
        self,
        request: ExternalTaskRequest,
        result: Optional[Dict[str, Any]],
        issue: Optional[ExternalIssue],
        error: bool,
    ) -> ExternalResponseEnvelope:
        """Assemble a schema-valid ExternalResponseEnvelope.

        Args:
            request: The original validated request (for trace_id echo).
            result: Result payload dict or None.
            issue: ExternalIssue to embed, or None.
            error: True → status="error"; False → status="ok".
        """
        return ExternalResponseEnvelope(
            status="error" if error else "ok",
            result=result,
            metadata={},
            issue=issue,
            trace_id=request.trace_id,
        )
