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


class ReporterError(GavelError):
    """
    Reporter generation errors (template loading, rendering, etc.).

    Use this exception when report generation fails due to:
    - Template file not found
    - Template rendering errors
    - Invalid context data
    - Output format errors

    Follow format: "<ErrorType>: <What happened> - <Recovery step>"
    """

    pass


class StorageError(GavelError):
    """
    Storage operation errors (save, load, file I/O, etc.).

    Use this exception when storage operations fail due to:
    - Directory creation failures
    - File read/write errors
    - Permission errors
    - Run not found errors

    Follow format: "<ErrorType>: <What happened> - <Recovery step>"
    """

    pass


class ResourceNotFoundError(StorageError):
    """
    Resource not found in storage (storage-agnostic).

    Use this exception when a requested resource does not exist:
    - Prompt template not found
    - Configuration file not found
    - Scenario data not found
    - Judge configuration not found

    This is storage-agnostic - applies to filesystem, database, API, etc.

    Follow format: "<ErrorType>: <What happened> - <Recovery step>"
    """

    pass
