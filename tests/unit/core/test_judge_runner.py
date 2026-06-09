"""
Unit tests for extended JudgeConfig validation (external-judge fields)
and the tier-classification matrix for external judge outcomes.

Covers:
- Task 41: JudgeConfig accepts protocol/config/system_id/abort-flag fields
- Task 44: Validation of external judge config shape + parametrized tier-classification matrix
"""

import pytest
from pydantic import ValidationError

from gavel_ai.core.issue_classifier import ExternalOutcome, classify_external_outcome
from gavel_ai.models.config import JudgeConfig

pytestmark = pytest.mark.unit


class TestJudgeConfigExternalFields:
    """Extended JudgeConfig validation for external-delegation fields (FR-7.1)."""

    def test_judge_config_defaults_to_no_protocol(self) -> None:
        """JudgeConfig without protocol is valid (in-process LLM judge)."""
        cfg = JudgeConfig(name="my-judge", type="deepeval.answer_relevancy")
        assert cfg.protocol is None
        assert cfg.system_id is None
        assert cfg.abort_on_exec_failure is True
        assert cfg.abort_on_process_error is False
        assert cfg.adapter == "gavel"

    def test_judge_config_accepts_http_protocol(self) -> None:
        """JudgeConfig with protocol='http' is valid."""
        cfg = JudgeConfig(
            name="http-judge",
            type="external",
            protocol="http",
            system_id="remote-judge-v1",
            config={"endpoint": "http://localhost:8080/judge", "method": "POST"},
            abort_on_exec_failure=True,
            abort_on_process_error=False,
        )
        assert cfg.protocol == "http"
        assert cfg.system_id == "remote-judge-v1"
        assert cfg.abort_on_exec_failure is True
        assert cfg.abort_on_process_error is False

    def test_judge_config_accepts_script_protocol(self) -> None:
        """JudgeConfig with protocol='script' is valid."""
        cfg = JudgeConfig(
            name="script-judge",
            type="external",
            protocol="script",
            system_id="script-judge-v1",
            config={"command": ["python", "judge.py"]},
        )
        assert cfg.protocol == "script"
        assert cfg.system_id == "script-judge-v1"

    def test_judge_config_http_rejects_command_in_config(self) -> None:
        """JudgeConfig with protocol='http' and 'command' in config raises ValueError."""
        with pytest.raises(ValidationError, match="command"):
            JudgeConfig(
                name="bad-http-judge",
                type="external",
                protocol="http",
                config={"command": ["python", "judge.py"]},
            )

    def test_judge_config_script_rejects_endpoint_in_config(self) -> None:
        """JudgeConfig with protocol='script' and 'endpoint' in config raises ValueError."""
        with pytest.raises(ValidationError, match="endpoint"):
            JudgeConfig(
                name="bad-script-judge",
                type="external",
                protocol="script",
                config={"endpoint": "http://localhost:8080/judge"},
            )

    def test_judge_config_abort_flags_default_values(self) -> None:
        """abort_on_exec_failure defaults True; abort_on_process_error defaults False."""
        cfg = JudgeConfig(
            name="j",
            type="external",
            protocol="http",
            config={"endpoint": "http://localhost:9999/judge"},
        )
        assert cfg.abort_on_exec_failure is True
        assert cfg.abort_on_process_error is False

    def test_judge_config_abort_flags_can_be_overridden(self) -> None:
        """Both abort flags can be set to non-default values."""
        cfg = JudgeConfig(
            name="j",
            type="external",
            protocol="script",
            config={"command": ["python", "j.py"]},
            abort_on_exec_failure=False,
            abort_on_process_error=True,
        )
        assert cfg.abort_on_exec_failure is False
        assert cfg.abort_on_process_error is True

    def test_judge_config_system_id_used_as_judge_id_override(self) -> None:
        """system_id, when set, is the intended judge_id value for JudgedRecord."""
        cfg = JudgeConfig(
            name="internal-name",
            type="external",
            protocol="script",
            system_id="public-judge-id",
            config={"command": ["python", "j.py"]},
        )
        assert cfg.system_id == "public-judge-id"

    def test_judge_config_adapter_defaults_to_gavel(self) -> None:
        """adapter field defaults to 'gavel'."""
        cfg = JudgeConfig(name="j", type="external", protocol="script", config={"command": ["python", "j.py"]})
        assert cfg.adapter == "gavel"

    def test_judge_config_adapter_can_be_set(self) -> None:
        """adapter field can be overridden."""
        cfg = JudgeConfig(
            name="j",
            type="external",
            protocol="script",
            config={"command": ["python", "j.py"]},
            adapter="custom-adapter",
        )
        assert cfg.adapter == "custom-adapter"

    def test_judge_config_rejects_invalid_protocol(self) -> None:
        """JudgeConfig with unsupported protocol value raises ValidationError."""
        with pytest.raises(ValidationError):
            JudgeConfig(
                name="bad-judge",
                type="external",
                protocol="grpc",  # type: ignore[arg-type]
            )


class TestJudgeExternalOutcomeTierClassification:
    """
    Parametrized tier-classification matrix for external judge outcomes.

    Mirrors the P2/P3 process-failure / process-success-with-issue cases,
    verifying the abort_on_exec_failure / abort_on_process_error orthogonality.
    """

    @pytest.mark.parametrize(
        "outcome,abort_on_exec_failure,abort_on_process_error,expected_tier",
        [
            # PROCESS_FAILURE: governed by abort_on_exec_failure; abort_on_process_error irrelevant
            (ExternalOutcome.PROCESS_FAILURE, True, True, "ERROR"),
            (ExternalOutcome.PROCESS_FAILURE, True, False, "ERROR"),
            (ExternalOutcome.PROCESS_FAILURE, False, True, "WARNING"),
            (ExternalOutcome.PROCESS_FAILURE, False, False, "WARNING"),
            # PROCESS_SUCCESS_WITH_ISSUE: governed by abort_on_process_error; abort_on_exec_failure irrelevant
            (ExternalOutcome.PROCESS_SUCCESS_WITH_ISSUE, True, True, "ERROR"),
            (ExternalOutcome.PROCESS_SUCCESS_WITH_ISSUE, False, True, "ERROR"),
            (ExternalOutcome.PROCESS_SUCCESS_WITH_ISSUE, True, False, "WARNING"),
            (ExternalOutcome.PROCESS_SUCCESS_WITH_ISSUE, False, False, "WARNING"),
            # None outcome always classifies as OK regardless of flags
            (None, True, True, "OK"),
            (None, True, False, "OK"),
            (None, False, True, "OK"),
            (None, False, False, "OK"),
        ],
    )
    def test_classify_external_outcome_judge_matrix(
        self,
        outcome: "ExternalOutcome | None",
        abort_on_exec_failure: bool,
        abort_on_process_error: bool,
        expected_tier: str,
    ) -> None:
        """classify_external_outcome maps (outcome, flags) to the expected IssueTier for judge configs."""
        result = classify_external_outcome(
            outcome,
            abort_on_exec_failure=abort_on_exec_failure,
            abort_on_process_error=abort_on_process_error,
        )
        assert result == expected_tier

    def test_process_failure_with_abort_raises_error_tier(self) -> None:
        """PROCESS_FAILURE + abort_on_exec_failure=True → 'ERROR' tier."""
        tier = classify_external_outcome(
            ExternalOutcome.PROCESS_FAILURE,
            abort_on_exec_failure=True,
            abort_on_process_error=False,
        )
        assert tier == "ERROR"

    def test_process_failure_without_abort_raises_warning_tier(self) -> None:
        """PROCESS_FAILURE + abort_on_exec_failure=False → 'WARNING' tier."""
        tier = classify_external_outcome(
            ExternalOutcome.PROCESS_FAILURE,
            abort_on_exec_failure=False,
            abort_on_process_error=False,
        )
        assert tier == "WARNING"

    def test_process_success_with_issue_and_abort_raises_error_tier(self) -> None:
        """PROCESS_SUCCESS_WITH_ISSUE + abort_on_process_error=True → 'ERROR' tier."""
        tier = classify_external_outcome(
            ExternalOutcome.PROCESS_SUCCESS_WITH_ISSUE,
            abort_on_exec_failure=False,
            abort_on_process_error=True,
        )
        assert tier == "ERROR"

    def test_process_success_with_issue_without_abort_is_warning(self) -> None:
        """PROCESS_SUCCESS_WITH_ISSUE + abort_on_process_error=False → 'WARNING' tier."""
        tier = classify_external_outcome(
            ExternalOutcome.PROCESS_SUCCESS_WITH_ISSUE,
            abort_on_exec_failure=True,
            abort_on_process_error=False,
        )
        assert tier == "WARNING"
