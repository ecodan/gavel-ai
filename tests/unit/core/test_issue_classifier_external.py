"""
Unit tests for `classify_external_outcome` (ADR-3 outcome -> IssueTier mapping).

Achieves full branch coverage of the function: outcome is None, PROCESS_FAILURE
(both abort_on_exec_failure states), and PROCESS_SUCCESS_WITH_ISSUE (both
abort_on_process_error states), confirming the orthogonal flag is irrelevant
in each branch.
"""

import pytest

from gavel_ai.core.issue_classifier import ExternalOutcome, IssueTier, classify_external_outcome

pytestmark = pytest.mark.unit


class TestClassifyExternalOutcome:
    """Full 8-case matrix for classify_external_outcome plus the None (OK) branch."""

    @pytest.mark.parametrize(
        "outcome,abort_on_exec_failure,abort_on_process_error,expected",
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
            # outcome is None always classifies as OK regardless of flags
            (None, True, True, "OK"),
            (None, True, False, "OK"),
            (None, False, True, "OK"),
            (None, False, False, "OK"),
        ],
    )
    def test_classify_external_outcome_matrix(
        self,
        outcome: "ExternalOutcome | None",
        abort_on_exec_failure: bool,
        abort_on_process_error: bool,
        expected: IssueTier,
    ) -> None:
        """classify_external_outcome maps (outcome, flags) to the expected IssueTier."""
        result = classify_external_outcome(
            outcome,
            abort_on_exec_failure=abort_on_exec_failure,
            abort_on_process_error=abort_on_process_error,
        )
        assert result == expected

    def test_default_adapter_is_gavel(self) -> None:
        """The default adapter ('gavel') is used when not explicitly specified."""
        explicit = classify_external_outcome(
            ExternalOutcome.PROCESS_FAILURE,
            abort_on_exec_failure=True,
            abort_on_process_error=False,
            adapter="gavel",
        )
        implicit = classify_external_outcome(
            ExternalOutcome.PROCESS_FAILURE,
            abort_on_exec_failure=True,
            abort_on_process_error=False,
        )
        assert explicit == implicit == "ERROR"
