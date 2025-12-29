"""Exception hierarchy for gavel-ai.

All gavel-ai exceptions inherit from GavelError for consistent error handling.
Error messages follow the pattern: <ErrorType>: <What happened> - <Recovery step>
"""


class GavelError(Exception):
    """Base exception for all gavel-ai errors."""

    pass


class ConfigError(GavelError):
    """Configuration-related errors (file, syntax, validation)."""

    pass


class ValidationError(GavelError):
    """Data validation errors (scenario format, etc.)."""

    pass


class ProcessorError(GavelError):
    """Processor execution errors (API call, timeout, etc.)."""

    pass


class JudgeError(GavelError):
    """Judge configuration or execution errors."""

    pass
