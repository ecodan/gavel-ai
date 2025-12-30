"""
Core module for gavel-ai.

Core models, configuration, and exceptions.

This module contains Pydantic data models, configuration loading, and custom exception hierarchy
used throughout the application.

"""

from gavel_ai.core.exceptions import GavelError, JudgeError, ProcessorError
from gavel_ai.core.models import (
    EvaluationResult,
    Input,
    JudgeConfig,
    JudgeEvaluation,
    JudgeResult,
    ProcessorConfig,
    ProcessorResult,
    Scenario,
)
from gavel_ai.core.result_storage import ResultStorage

# Export public API
__all__ = [
    "Input",
    "ProcessorConfig",
    "ProcessorResult",
    "Scenario",
    "JudgeConfig",
    "JudgeResult",
    "JudgeEvaluation",
    "EvaluationResult",
    "ResultStorage",
    "GavelError",
    "ProcessorError",
    "JudgeError",
]
