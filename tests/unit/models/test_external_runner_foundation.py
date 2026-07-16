"""
Unit tests for external-runner foundation models.

Covers:
- TestSubject protocol/abort_on_*/adapter validation
- EvalConfig test_subject_type validation, including the deprecated
  'in-situ' -> 'external' alias normalization with WARNING-tier logging
- ScriptSystemInput, ExternalIssue, ExternalResponseEnvelope construction
- JudgedRecord.metadata default and round-trip
"""

import logging

import pytest
from pydantic import ValidationError

from gavel_ai.models.config import EvalConfig, JudgeConfig, ScenariosConfig, TestSubject
from gavel_ai.models.runtime import (
    ExternalIssue,
    ExternalResponseEnvelope,
    JudgedRecord,
    ScriptSystemInput,
)

pytestmark = pytest.mark.unit


def _make_eval_config(test_subject_type: str) -> EvalConfig:
    """Build a minimal valid EvalConfig with the given test_subject_type."""
    return EvalConfig(
        eval_type="oneshot",
        eval_name="test-eval",
        test_subject_type=test_subject_type,
        test_subjects=[
            TestSubject(
                prompt_name="prompt",
                judges=[JudgeConfig(name="test", type="test.type")],
            ),
        ],
        variants=["variant1"],
        scenarios=ScenariosConfig(source="file.local", name="scenarios.json"),
    )


class TestTestSubjectProtocol:
    """Test TestSubject.protocol validation and protocol-specific config rules."""

    @pytest.mark.parametrize("protocol", ["http", "script", None])
    def test_valid_protocol_values(self, protocol: str) -> None:
        """Valid protocol values (http, script, or omitted) construct successfully."""
        subject = TestSubject(
            prompt_name="prompt",
            judges=[JudgeConfig(name="test", type="test.type")],
            protocol=protocol,
        )
        assert subject.protocol == protocol

    def test_invalid_protocol_raises(self) -> None:
        """An unrecognized protocol value raises ValidationError naming 'protocol'."""
        with pytest.raises(ValidationError) as exc_info:
            TestSubject(
                prompt_name="prompt",
                judges=[JudgeConfig(name="test", type="test.type")],
                protocol="bogus",
            )
        assert "protocol" in str(exc_info.value)

    def test_http_protocol_rejects_command_in_config(self) -> None:
        """protocol='http' with a 'command' key in config raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TestSubject(
                prompt_name="prompt",
                judges=[JudgeConfig(name="test", type="test.type")],
                protocol="http",
                config={"command": ["./run.sh"]},
            )
        assert "command" in str(exc_info.value)

    def test_script_protocol_rejects_endpoint_in_config(self) -> None:
        """protocol='script' with an 'endpoint' key in config raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TestSubject(
                prompt_name="prompt",
                judges=[JudgeConfig(name="test", type="test.type")],
                protocol="script",
                config={"endpoint": "https://example.com"},
            )
        assert "endpoint" in str(exc_info.value)

    def test_http_protocol_accepts_endpoint_config(self) -> None:
        """protocol='http' with endpoint-shaped config constructs successfully."""
        subject = TestSubject(
            prompt_name="prompt",
            judges=[JudgeConfig(name="test", type="test.type")],
            protocol="http",
            config={"endpoint": "https://example.com", "method": "POST"},
        )
        assert subject.config == {"endpoint": "https://example.com", "method": "POST"}

    def test_script_protocol_accepts_command_config(self) -> None:
        """protocol='script' with command-shaped config constructs successfully."""
        subject = TestSubject(
            prompt_name="prompt",
            judges=[JudgeConfig(name="test", type="test.type")],
            protocol="script",
            config={"command": ["./run.sh"], "timeout": 30},
        )
        assert subject.config == {"command": ["./run.sh"], "timeout": 30}


class TestTestSubjectAbortFlagsAndAdapter:
    """Test TestSubject abort_on_* defaults/overrides and adapter default/equivalence."""

    def test_abort_flag_defaults(self) -> None:
        """abort_on_exec_failure defaults True, abort_on_process_error defaults False."""
        subject = TestSubject(
            prompt_name="prompt",
            judges=[JudgeConfig(name="test", type="test.type")],
        )
        assert subject.abort_on_exec_failure is True
        assert subject.abort_on_process_error is False

    @pytest.mark.parametrize(
        "abort_on_exec_failure,abort_on_process_error",
        [
            (True, True),
            (True, False),
            (False, True),
            (False, False),
        ],
    )
    def test_abort_flag_explicit_overrides(
        self, abort_on_exec_failure: bool, abort_on_process_error: bool
    ) -> None:
        """Explicit abort_on_* overrides are respected for all combinations."""
        subject = TestSubject(
            prompt_name="prompt",
            judges=[JudgeConfig(name="test", type="test.type")],
            abort_on_exec_failure=abort_on_exec_failure,
            abort_on_process_error=abort_on_process_error,
        )
        assert subject.abort_on_exec_failure is abort_on_exec_failure
        assert subject.abort_on_process_error is abort_on_process_error

    def test_adapter_defaults_to_gavel(self) -> None:
        """adapter defaults to 'gavel' when omitted."""
        subject = TestSubject(
            prompt_name="prompt",
            judges=[JudgeConfig(name="test", type="test.type")],
        )
        assert subject.adapter == "gavel"

    def test_adapter_explicit_gavel_is_equivalent_to_omission(self) -> None:
        """Explicitly passing adapter='gavel' produces an identical model to omitting it."""
        omitted = TestSubject(
            prompt_name="prompt",
            judges=[JudgeConfig(name="test", type="test.type")],
        )
        explicit = TestSubject(
            prompt_name="prompt",
            judges=[JudgeConfig(name="test", type="test.type")],
            adapter="gavel",
        )
        assert omitted.adapter == explicit.adapter == "gavel"
        assert omitted.model_dump() == explicit.model_dump()

    def test_adapter_override(self) -> None:
        """A non-default adapter value is accepted and stored verbatim."""
        subject = TestSubject(
            prompt_name="prompt",
            judges=[JudgeConfig(name="test", type="test.type")],
            adapter="custom-adapter",
        )
        assert subject.adapter == "custom-adapter"


class TestEvalConfigTestSubjectTypeValidation:
    """Test EvalConfig.test_subject_type validation and the in-situ alias."""

    @pytest.mark.parametrize("value", ["local", "external"])
    def test_valid_test_subject_type_values(self, value: str) -> None:
        """'local' and 'external' validate and pass through unchanged."""
        config = _make_eval_config(value)
        assert config.test_subject_type == value

    def test_invalid_test_subject_type_raises(self) -> None:
        """An unrecognized test_subject_type raises ValidationError naming the value."""
        with pytest.raises(ValidationError) as exc_info:
            _make_eval_config("bogus")
        assert "test_subject_type" in str(exc_info.value)

    def test_in_situ_normalizes_to_external(self, caplog: pytest.LogCaptureFixture) -> None:
        """'in-situ' is normalized to 'external' and emits exactly one WARNING log."""
        with caplog.at_level(logging.WARNING, logger="gavel_ai.models.config"):
            config = _make_eval_config("in-situ")

        assert config.test_subject_type == "external"

        warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warning_records) == 1
        message = warning_records[0].getMessage()
        assert "in-situ" in message
        assert "external" in message


class TestScriptSystemInput:
    """Test ScriptSystemInput construction and command validation."""

    def test_create_basic(self) -> None:
        """Create ScriptSystemInput with required fields and check defaults."""
        input_item = ScriptSystemInput(
            id="script-001",
            command=["./run.sh", "--flag"],
            request_payload={"prompt": "hello"},
        )
        assert input_item.id == "script-001"
        assert input_item.command == ["./run.sh", "--flag"]
        assert input_item.working_dir is None
        assert input_item.request_payload == {"prompt": "hello"}
        assert input_item.request_filename == "request.json"
        assert input_item.response_filename == "response.json"

    def test_create_with_overrides(self) -> None:
        """Create ScriptSystemInput with all optional fields overridden."""
        input_item = ScriptSystemInput(
            id="script-002",
            command=["python", "main.py"],
            working_dir="/tmp/work",
            request_payload={"prompt": "hello"},
            request_filename="req.json",
            response_filename="resp.json",
        )
        assert input_item.working_dir == "/tmp/work"
        assert input_item.request_filename == "req.json"
        assert input_item.response_filename == "resp.json"

    def test_command_as_bare_string_raises(self) -> None:
        """A bare string for command raises ValidationError (not coerced to char list)."""
        with pytest.raises(ValidationError) as exc_info:
            ScriptSystemInput(
                id="script-003",
                command="./run.sh",  # type: ignore[arg-type]
                request_payload={"prompt": "hello"},
            )
        assert "command" in str(exc_info.value)


class TestExternalIssue:
    """Test ExternalIssue construction."""

    @pytest.mark.parametrize("level", ["error", "warning"])
    def test_create_valid(self, level: str) -> None:
        """Create ExternalIssue with valid severity levels."""
        issue = ExternalIssue(code="TIMEOUT", level=level, message="The process timed out")
        assert issue.code == "TIMEOUT"
        assert issue.level == level
        assert issue.message == "The process timed out"

    def test_invalid_level_raises(self) -> None:
        """An unrecognized level value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ExternalIssue(code="TIMEOUT", level="critical", message="boom")  # type: ignore[arg-type]
        assert "level" in str(exc_info.value)


class TestExternalResponseEnvelope:
    """Test ExternalResponseEnvelope construction and round-trip via model_validate."""

    def test_validate_status_ok(self) -> None:
        """A status='ok' envelope parses with result/metadata/trace_id."""
        envelope = ExternalResponseEnvelope.model_validate(
            {
                "status": "ok",
                "result": {"answer": "42"},
                "metadata": {"timing_ms": 120},
                "trace_id": "trace-abc",
            }
        )
        assert envelope.status == "ok"
        assert envelope.result == {"answer": "42"}
        assert envelope.metadata == {"timing_ms": 120}
        assert envelope.issue is None
        assert envelope.trace_id == "trace-abc"

    def test_validate_status_ok_with_issue(self) -> None:
        """A status='ok' envelope may carry an issue (PROCESS_SUCCESS_WITH_ISSUE)."""
        envelope = ExternalResponseEnvelope.model_validate(
            {
                "status": "ok",
                "result": {"answer": "partial"},
                "issue": {"code": "PARTIAL", "level": "warning", "message": "Degraded result"},
            }
        )
        assert envelope.status == "ok"
        assert envelope.issue is not None
        assert envelope.issue.code == "PARTIAL"
        assert envelope.issue.level == "warning"

    def test_validate_status_error_with_issue(self) -> None:
        """A status='error' envelope parses with a structured issue."""
        envelope = ExternalResponseEnvelope.model_validate(
            {
                "status": "error",
                "issue": {"code": "CRASH", "level": "error", "message": "Process crashed"},
            }
        )
        assert envelope.status == "error"
        assert envelope.issue is not None
        assert envelope.issue.code == "CRASH"
        assert envelope.issue.level == "error"
        assert envelope.result is None

    def test_validate_invalid_status_raises(self) -> None:
        """An unrecognized status value raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ExternalResponseEnvelope.model_validate({"status": "bogus"})
        assert "status" in str(exc_info.value)


class TestJudgedRecordMetadata:
    """Test JudgedRecord.metadata default and round-trip serialization."""

    def _make_record(self, **overrides: object) -> JudgedRecord:
        base: dict = dict(
            test_subject="subject-1",
            variant_id="variant-1",
            scenario_id="scenario-1",
            judge_id="judge-1",
            score=0.8,
            timestamp="2026-01-01T00:00:00Z",
        )
        base.update(overrides)
        return JudgedRecord(**base)

    def test_metadata_defaults_to_empty_dict(self) -> None:
        """JudgedRecord.metadata defaults to an empty dict when omitted."""
        record = self._make_record()
        assert record.metadata == {}

    def test_metadata_round_trips_through_model_dump(self) -> None:
        """JudgedRecord.metadata survives a model_dump() round-trip."""
        record = self._make_record(metadata={"trace_id": "trace-xyz"})
        dumped = record.model_dump()
        assert dumped["metadata"] == {"trace_id": "trace-xyz"}
        rebuilt = JudgedRecord(**dumped)
        assert rebuilt.metadata == {"trace_id": "trace-xyz"}

    def test_metadata_round_trips_through_model_dump_json(self) -> None:
        """JudgedRecord.metadata survives a model_dump_json() round-trip."""
        record = self._make_record(metadata={"trace_id": "trace-xyz", "turn": 2})
        json_str = record.model_dump_json()
        rebuilt = JudgedRecord.model_validate_json(json_str)
        assert rebuilt.metadata == {"trace_id": "trace-xyz", "turn": 2}
