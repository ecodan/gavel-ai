"""
Core data models for gavel-ai processors, judges, and reporters.

DEPRECATED: This module is now located at gavel_ai.models.runtime

Please use:
  from gavel_ai.models import Input, ProcessorConfig, etc.
  from gavel_ai.models.runtime import Input, ProcessorConfig, etc.
"""

# Backward compatibility: Re-export from new location
from gavel_ai.models import (
    ArtifactRef,
    EvaluationResult,
    Input,
    JudgedRecord,
    JudgeEvaluation,
    JudgeResult,
    Manifest,
    OutputRecord,
    ProcessorConfig,
    ProcessorResult,
    ReporterConfig,
    Scenario,
)

__all__ = [
    "ArtifactRef",
    "EvaluationResult",
    "Input",
    "JudgeEvaluation",
    "JudgeResult",
    "Manifest",
    "OutputRecord",
    "JudgedRecord",
    "ProcessorConfig",
    "ProcessorResult",
    "ReporterConfig",
    "Scenario",
]
