"""
Three-tier issue classifier for eval run errors.

Tiers:
  ERROR   — HTTP 4xx/5xx from LLM providers, rate-limit responses, unclassified
             exceptions during task/judge execution.
  WARNING — Schema/config validation failures that are non-fatal.
  OK      — Reserved; not raised as exceptions.
"""

from enum import Enum
from typing import Callable, Dict, Literal, Optional, Type

IssueTier = Literal["ERROR", "WARNING", "OK"]

_RATE_LIMIT_MARKERS = ("429", "rate limit", "ratelimit", "too many requests")
_HTTP_ERROR_MARKERS = ("http 4", "http 5", "status 4", "status 5", "status_code=4", "status_code=5")

# Module-level lazy imports to avoid circular deps at parse time
try:
    from pydantic import ValidationError as _PydanticValidationError
except ImportError:
    _PydanticValidationError = None  # type: ignore[assignment,misc]

try:
    from gavel_ai.core.exceptions import ConfigError as _ConfigError
except ImportError:
    _ConfigError = None  # type: ignore[assignment]


def classify(exc: BaseException) -> IssueTier:
    """
    Classify an exception raised during task or judge execution.

    Rules (checked in order):
    1. Schema/config validation errors → WARNING
    2. HTTP 4xx/5xx or rate-limit signals → ERROR
    3. Everything else → ERROR
    """
    if _PydanticValidationError is not None and isinstance(exc, _PydanticValidationError):
        return "WARNING"
    if _ConfigError is not None and isinstance(exc, _ConfigError):
        return "WARNING"

    msg = str(exc).lower()

    if any(k in msg for k in _RATE_LIMIT_MARKERS):
        return "ERROR"
    if any(k in msg for k in _HTTP_ERROR_MARKERS):
        return "ERROR"

    return "ERROR"


def classify_message(msg: str) -> IssueTier:
    """Classify an error by its string message (no exception type inspection)."""
    lowered = msg.lower()
    if any(k in lowered for k in _RATE_LIMIT_MARKERS):
        return "ERROR"
    if any(k in lowered for k in _HTTP_ERROR_MARKERS):
        return "ERROR"
    return "ERROR"


class ExternalOutcome(str, Enum):
    """Transport-observed outcomes for an external runner adapter invocation."""

    PROCESS_FAILURE = "process_failure"
    PROCESS_SUCCESS_WITH_ISSUE = "process_success_with_issue"


def _classify_gavel_outcome(
    outcome: ExternalOutcome,
    abort_on_exec_failure: bool,
    abort_on_process_error: bool,
) -> IssueTier:
    """Default (gavel) mapping from `ExternalOutcome` + Builder flags to `IssueTier`."""
    if outcome is ExternalOutcome.PROCESS_FAILURE:
        return "ERROR" if abort_on_exec_failure else "WARNING"
    return "ERROR" if abort_on_process_error else "WARNING"


# Adapter-keyed outcome classifiers. Adding support for a new external runner
# adapter means registering its mapping here rather than branching inline.
_OUTCOME_CLASSIFIERS: Dict[str, Callable[[ExternalOutcome, bool, bool], IssueTier]] = {
    "gavel": _classify_gavel_outcome,
}


def classify_external_outcome(
    outcome: Optional[ExternalOutcome],
    abort_on_exec_failure: bool,
    abort_on_process_error: bool,
    adapter: str = "gavel",
) -> IssueTier:
    """
    Map a transport-observed external-runner outcome onto the `IssueTier` vocabulary.

    `outcome` is `None` when the run completed without an external-runner issue,
    which always classifies as `OK`. Otherwise the mapping is delegated to the
    adapter-specific classifier registered in `_OUTCOME_CLASSIFIERS` (defaulting
    to `"gavel"`), parameterized by the Builder's abort-on-* flags.
    """
    if outcome is None:
        return "OK"
    classifier = _OUTCOME_CLASSIFIERS[adapter]
    return classifier(outcome, abort_on_exec_failure, abort_on_process_error)
