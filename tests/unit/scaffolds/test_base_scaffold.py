"""
Unit tests for gavel_ai.scaffolds — base, remote, and script scaffold classes.

Tests cover:
- Import isolation: importing scaffold classes must NOT pull in gavel_ai.core.*
- Round-trip: minimal subclass processes a real-fixture request → schema-valid envelope
- Malformed request: clear error naming the field and schema doc path
- handle() raises → status="error"
- handle() returns ExternalIssue → status="ok" with issue populated
- Structured log line carrying trace_id is emitted per invocation
"""

import logging
import sys
from typing import Any, Dict, Optional

import pytest

from gavel_ai.models.runtime import ExternalIssue, ExternalResponseEnvelope, ExternalTaskRequest

# ── Constants ────────────────────────────────────────────────────────────────
_SCHEMA_DOC = "schema-external-runner.md"

# ── Real-fixture request dict (mirrors Partition 2/3 fixture scripts) ────────
_VALID_REQUEST: Dict[str, Any] = {
    "scenario_id": "greet-en-001",
    "scenario_input": "Hello, how are you?",
    "rendered_prompt": "You are a helpful assistant.\n\nUser: Hello, how are you?\nAssistant:",
    "custom_config": {"model": "test-model"},
    "trace_id": "run-test-abc123",
    "metadata": {"variant_id": "v1"},
}


# ── Minimal concrete subclasses ───────────────────────────────────────────────

class _EchoHTTPSUT:
    """Inline subclass (avoids importing RemoteSystemUnderTest before isolation check)."""
    pass


# ── Task 56 — Import isolation ────────────────────────────────────────────────

@pytest.mark.unit
def test_import_scaffold_does_not_pull_in_core() -> None:
    """Importing RemoteSystemUnderTest / ScriptSystemUnderTest must not load gavel_ai.core.*"""
    # Snapshot of loaded modules before import
    before: set = {k for k in sys.modules if k.startswith("gavel_ai.core")}

    from gavel_ai.scaffolds import RemoteSystemUnderTest, ScriptSystemUnderTest  # noqa: F401

    after: set = {k for k in sys.modules if k.startswith("gavel_ai.core")}
    new_core_modules = after - before

    assert not new_core_modules, (
        f"Importing scaffold classes pulled in core modules: {new_core_modules}"
    )


# ── Task 61 — Round-trip tests ────────────────────────────────────────────────

@pytest.mark.unit
def test_remote_sut_round_trip() -> None:
    """Minimal RemoteSystemUnderTest subclass → schema-valid ExternalResponseEnvelope."""
    from gavel_ai.scaffolds import RemoteSystemUnderTest

    class EchoSUT(RemoteSystemUnderTest):
        def handle(self, request: ExternalTaskRequest) -> Dict[str, Any]:
            return {"output": f"echo:{request.scenario_id}"}

    sut = EchoSUT()
    response: Dict[str, Any] = sut.handle_http_request(_VALID_REQUEST)

    # Must parse as ExternalResponseEnvelope (schema validity check)
    envelope = ExternalResponseEnvelope.model_validate(response)
    assert envelope.status == "ok"
    assert envelope.result is not None
    assert envelope.result["output"] == "echo:greet-en-001"
    assert envelope.trace_id == "run-test-abc123"
    assert envelope.issue is None


@pytest.mark.unit
def test_script_sut_round_trip() -> None:
    """Minimal ScriptSystemUnderTest subclass → schema-valid ExternalResponseEnvelope."""
    from gavel_ai.scaffolds import ScriptSystemUnderTest

    class EchoScript(ScriptSystemUnderTest):
        def handle(self, request: ExternalTaskRequest) -> Dict[str, Any]:
            return {"output": f"echo:{request.scenario_id}"}

    sut = EchoScript()
    envelope: ExternalResponseEnvelope = sut.process(_VALID_REQUEST)

    assert ExternalResponseEnvelope.model_validate(envelope.model_dump())
    assert envelope.status == "ok"
    assert envelope.result == {"output": "echo:greet-en-001"}
    assert envelope.trace_id == "run-test-abc123"


# ── Malformed request rejection ────────────────────────────────────────────────

@pytest.mark.unit
def test_malformed_request_names_field_and_schema_doc() -> None:
    """_parse_and_validate should raise ScaffoldValidationError with field name and schema doc path."""
    from gavel_ai.scaffolds import RemoteSystemUnderTest
    from gavel_ai.scaffolds.base import ScaffoldValidationError

    class EchoSUT(RemoteSystemUnderTest):
        def handle(self, request: ExternalTaskRequest) -> Dict[str, Any]:
            return {}

    sut = EchoSUT()
    bad_request: Dict[str, Any] = {
        # Missing required fields: scenario_id, scenario_input, rendered_prompt
        "metadata": {"variant_id": "v1"},
    }

    with pytest.raises(ScaffoldValidationError) as exc_info:
        sut.process(bad_request)

    msg = str(exc_info.value)
    # Must name a missing field
    assert "scenario_id" in msg or "scenario_input" in msg or "rendered_prompt" in msg
    # Must reference the schema doc
    assert _SCHEMA_DOC in msg


@pytest.mark.unit
def test_malformed_request_wrong_type_names_field() -> None:
    """Field type mismatch must also name the field in the error."""
    from gavel_ai.scaffolds import ScriptSystemUnderTest
    from gavel_ai.scaffolds.base import ScaffoldValidationError

    class EchoScript(ScriptSystemUnderTest):
        def handle(self, request: ExternalTaskRequest) -> Dict[str, Any]:
            return {}

    sut = EchoScript()
    bad_request: Dict[str, Any] = {
        "scenario_id": 12345,          # must be str
        "scenario_input": "input",
        "rendered_prompt": "prompt",
    }

    with pytest.raises(ScaffoldValidationError) as exc_info:
        sut.process(bad_request)

    msg = str(exc_info.value)
    assert _SCHEMA_DOC in msg


# ── handle raises → status: "error" ───────────────────────────────────────────

@pytest.mark.unit
def test_handle_raises_assembles_error_status() -> None:
    """When handle() raises, the response envelope must have status='error'."""
    from gavel_ai.scaffolds import RemoteSystemUnderTest

    class FailSUT(RemoteSystemUnderTest):
        def handle(self, request: ExternalTaskRequest) -> Dict[str, Any]:
            raise RuntimeError("something went wrong")

    sut = FailSUT()
    envelope: ExternalResponseEnvelope = sut.process(_VALID_REQUEST)

    assert envelope.status == "error"
    assert envelope.issue is not None
    assert "something went wrong" in envelope.issue.message
    # Must still be schema-valid
    ExternalResponseEnvelope.model_validate(envelope.model_dump())


@pytest.mark.unit
def test_handle_raises_schema_valid() -> None:
    """Error envelope must parse as ExternalResponseEnvelope without raising."""
    from gavel_ai.scaffolds import ScriptSystemUnderTest

    class FailScript(ScriptSystemUnderTest):
        def handle(self, request: ExternalTaskRequest) -> Dict[str, Any]:
            raise ValueError("oops")

    sut = FailScript()
    envelope = sut.process(_VALID_REQUEST)
    parsed = ExternalResponseEnvelope.model_validate(envelope.model_dump())
    assert parsed.status == "error"


# ── handle returns ExternalIssue → status: "ok" with issue ────────────────────

@pytest.mark.unit
def test_handle_returns_issue_populates_issue_field() -> None:
    """handle() returning ExternalIssue → status='ok', issue populated."""
    from gavel_ai.scaffolds import RemoteSystemUnderTest

    class WarningSUT(RemoteSystemUnderTest):
        def handle(self, request: ExternalTaskRequest) -> ExternalIssue:
            return ExternalIssue(
                code="low_confidence",
                level="warning",
                message="model confidence below threshold",
            )

    sut = WarningSUT()
    envelope = sut.process(_VALID_REQUEST)

    assert envelope.status == "ok"
    assert envelope.issue is not None
    assert envelope.issue.code == "low_confidence"
    assert envelope.issue.level == "warning"
    # Schema-valid
    ExternalResponseEnvelope.model_validate(envelope.model_dump())


# ── Structured log line with trace_id ─────────────────────────────────────────

@pytest.mark.unit
def test_handle_emits_log_with_trace_id(caplog: pytest.LogCaptureFixture) -> None:
    """A structured log line carrying trace_id must be emitted per handle invocation."""
    from gavel_ai.scaffolds import RemoteSystemUnderTest

    class LogSUT(RemoteSystemUnderTest):
        def handle(self, request: ExternalTaskRequest) -> Dict[str, Any]:
            return {"output": "ok"}

    sut = LogSUT()

    with caplog.at_level(logging.INFO, logger="gavel-ai.scaffolds"):
        sut.process(_VALID_REQUEST)

    log_text = " ".join(caplog.messages)
    assert "run-test-abc123" in log_text  # trace_id
    assert "greet-en-001" in log_text  # scenario_id


@pytest.mark.unit
def test_handle_no_trace_id_logs_none(caplog: pytest.LogCaptureFixture) -> None:
    """trace_id=None should still emit a log (no crash)."""
    from gavel_ai.scaffolds import RemoteSystemUnderTest

    class LogSUT(RemoteSystemUnderTest):
        def handle(self, request: ExternalTaskRequest) -> Dict[str, Any]:
            return {"output": "ok"}

    sut = LogSUT()
    request_no_trace = {**_VALID_REQUEST, "trace_id": None}

    with caplog.at_level(logging.INFO, logger="gavel-ai.scaffolds"):
        envelope = sut.process(request_no_trace)

    assert envelope.status == "ok"
    assert envelope.trace_id is None
